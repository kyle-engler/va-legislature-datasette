import contextlib
import csv
from csv import excel
from datetime import date
from enum import Enum
from importlib import resources
from itertools import zip_longest
from typing import Dict, Iterable, Iterator

from sqlite_utils import Database, recipes
from sqlite_utils.utils import Format
from sqlite_utils.utils import rows_from_file as rows_from_file_implementation

from va_legislature_datasette import lis_data

db = Database("lis.db")


class Conversion(Enum):
    Trim = "trim(?)"


def load():
    """Our main entry point. Execute ELT for all the inputs."""
    load_members()
    load_committees()
    load_committee_members()
    load_bills()
    load_bill_subjects()
    load_parent_child_subjects()
    load_docket()
    load_history()


def load_members():
    db.table("members", pk="MBR_MBRNO").insert_all(
        rows_from_file("Members.csv"),
        conversions={"MBR_NAME": Conversion.Trim.value},
        replace=True,
    )


def load_committees():
    db.table("committees", pk="COM_COMNO").insert_all(
        rows_from_file("Committees.csv"),
        conversions={"COM_NAME": Conversion.Trim.value},
        replace=True,
    )


def load_committee_members():
    db.table(
        "committee_members",
        foreign_keys=[
            ("CMB_COMNO", "committees", "COM_COMNO"),
            ("CMB_MBRNO", "members", "MBR_MBRNO"),
        ],
    ).insert_all(
        rows_from_file("CommitteeMembers.csv"),
        replace=True,
    )


def load_bills():
    db.table(
        "bills",
        pk="Bill_id",
        foreign_keys=[
            ("Patron_id", "members", "MBR_MBRNO"),
            ("Last_house_committee_id", "committees", "COM_COMNO"),
            ("Last_senate_committee_id", "committees", "COM_COMNO"),
        ],
        replace=True,
    ).insert_all(rows_from_file("BILLS.csv")).convert(
        [
            "Last_house_action_date",
            "Last_senate_action_date",
            "Last_conference_action_date",
            "Last_governor_action_date",
            "Introduction_date",
        ],
        fn=recipes.parsedate,
        output_type=date,
    )


def load_bill_subjects():
    """TODO turn this into conformed dimensional lookup table"""
    db.table("bills_subjects").create(
        {"Bill_Number": str, "Subject_Name": str, "Subject_Id": int},
        pk=("Bill_Number", "Subject_Name", "Subject_Id"),
        foreign_keys=[("Bill_Number", "bills", "Bill_id")],
        replace=True,
    ).insert_all(rows_from_file("CIBillSubjects.csv"))


def load_parent_child_subjects():
    db.table("parent_child_subjects").create(
        columns={
            "Parent_Subject": str,
            "P_Subject_Id": int,
            "Child_Subject": str,
            "C_Subject_Id": int,
        },
        pk=("P_Subject_Id", "C_Subject_Id"),
        replace=True,
    ).insert_all(rows_from_file("CIParentChildSubjects.csv"))


def load_docket():
    db.table("dockets").create(
        columns={"Com_no": str, "Doc_date": date, "Doc_no": int, "Bill_no": str},
        foreign_keys=[
            ("Com_no", "committees", "COM_COMNO"),
            ("Bill_no", "bills", "Bill_id"),
        ],
        replace=True,
    ).insert_all(rows_from_file("DOCKET.csv")).convert("Doc_date", fn=recipes.parsedate)


def load_history():
    db.table("history").create(
        columns={
            "Bill_id": str,
            "History_date": str,
            "History_description": str,
            "History_refid": str,
        },
        replace=True,
        foreign_keys=[("Bill_id", "bills", "Bill_id")],
    ).insert_all(
        rows_from_file("HISTORY.csv"),
        conversions={
            "History_description": Conversion.Trim.value,
            "History_refid": Conversion.Trim.value,
        },
    )


def load_sponsors():
    """
    Todo this needs work because PATRON TYPE field is malforemed,
    the source doesn't properly escape the quotes in the field value
    """
    db.table("sponsors").create(
        columns={
            "MEMBER_NAME": str,
            "MEMBER_ID": str,
            "BILL_NUMBER": str,
            "PATRON_TYPE": str,
        },
        replace=True,
        foreign_keys=[("MEMBER_ID", "members", "MBR_MBRNO")],
    )
    # Todo
    # .insert_all(
    #     rows_from_file("Sponsors.csv"),
    #     conversions={
    #         "MEMBER_NAME": Conversion.Trim.value,
    #         "History_refid": Conversion.Trim.value
    #     },
    # )


def rows_from_file(file_name: str) -> Iterable[Dict]:
    """Generates dictionary records from most source CSV rows

    .. note:: For now, we bake the CSV input data into the package so it's easy to find.

    .. warning:: Some files like `VOTE.csv` are wonky and require custom extracts

    Args:
        file_name: The name of the CSV File

    Returns:
        Generator of rows
    """
    # I am not a fan of the 3.11+ resource recommendation. This reads
    # much worse than the old style!
    # noinspection PyTypeChecker
    with open_resource(file_name) as resource:
        file = open(resource, "rb")
        row_gen, _ = rows_from_file_implementation(
            file, format=Format.CSV, dialect=excel, encoding="utf-8-sig"
        )
        for data in row_gen:
            yield data


@contextlib.contextmanager
def open_resource(file_name: str):
    """
    Use the recommended 3.11+ method for opening package data.

    I'm not a fan. This reads much worse than the old style!
    """
    # noinspection PyTypeChecker
    with resources.as_file(resources.files(lis_data).joinpath(file_name)) as resource:
        yield resource


def generate_vote_data() -> Iterator[Dict]:
    """
    Yield data from the Votes file.

    The votes file sucks. The data is an optional number of member number / vote value pairs transposed as columns!
    Worse, for reasons, I don't yet understand, a vote row can have a History_refid without any voting columns.
    SQLite does not treat nulls as equal in unique constraints, so best to just skip rows without any
    voting data.

    Returns:
        Dictionary of data!
    """
    # We can't use the built-in tools because the data is so fucked
    with open_resource("VOTE.csv") as resource:
        with open(resource, newline="") as f:
            reader = csv.reader(f)
            for row in reader:
                # For reasons, I don't yet understand, a vote row can have an id without any key value pairs.
                # SQLite doesn't treat nulls as equal in unique constraints, so best to just skip
                # vote rows that don't have any members participating at all.
                history_refid, *rest = row
                if not rest:
                    continue
                for member_number, vote_status in grouper(rest, 2, incomplete="strict"):
                    yield {
                        "History_refid": history_refid,
                        "MBR_MBRNO": member_number,
                        "vote_status": vote_status,
                    }


def grouper(iterable, n, *, incomplete="strict", fillvalue=None):
    """Taken from the itertools recipes, Python 3.13+ users can use batched"""
    # grouper('ABCDEFG', 3, fillvalue='x') --> ABC DEF Gxx
    # grouper('ABCDEFG', 3, incomplete='strict') --> ABC DEF ValueError
    # grouper('ABCDEFG', 3, incomplete='ignore') --> ABC DEF
    args = [iter(iterable)] * n
    if incomplete == "fill":
        # noinspection PyArgumentList
        return zip_longest(*args, fillvalue=fillvalue)
    if incomplete == "strict":
        return zip(*args, strict=True)
    if incomplete == "ignore":
        return zip(*args)
    else:
        raise ValueError("Expected fill, strict, or ignore")


if __name__ == "__main__":
    load()
