import pytest

from va_legislature_datasette.load import rows_from_file, generate_vote_data


@pytest.mark.parametrize(
    "filename",
    [
        "Amendments.csv",
        "BILLS.csv",
        "CIBillSubjects.csv",
        "CIParentChildSubjects.csv",
        "CommitteeMembers.csv",
        "Committees.csv",
        "DOCKET.csv",
        "FiscalImpactStatements.csv",
        "HISTORY.csv",
        "Members.csv",
        "Sponsors.csv",
        "SubCommitteeMembers.csv",
        "SUBDOCKET.csv",
        "Summaries.csv",
        # "VOTE.csv", - This file will require a transform
        "VoteStatements.csv",
    ],
)
def test_can_read_csv(filename):
    row_gen = rows_from_file(filename)
    data = list(row_gen)
    assert data


def test_can_process_vote_file():
    gen = generate_vote_data()
    data = list(gen)
    assert data
