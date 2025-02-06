import asyncio

import aiofiles
import httpx
import pytest

from va_legislature_datasette.extract import (FILES_ENDPOINT,
                                              async_download_file,
                                              download_all_files,
                                              legislative_session_identifier)
from va_legislature_datasette.load import (generate_vote_data, open_resource,
                                           rows_from_file)


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


@pytest.fixture
def package_test_file():
    """Guarantee the test file state"""
    with open_resource("Test.txt") as f:
        f.write_text("This is a test")

    yield

    with open_resource("Test.txt") as f:
        f.write_text("This is a test")


@pytest.fixture(scope="session")
def async_client():
    return httpx.AsyncClient()


@pytest.fixture(scope="session")
def current_session_code():
    return legislative_session_identifier(FILES_ENDPOINT)


def test_can_async_rewrite_package_resource_at_run_time(package_test_file):
    """This proves we can open the package resource syncronously and write to the resource asyncronously"""

    async def async_write_test():
        with open_resource("Test.txt") as f:
            async with aiofiles.open(f, "wt") as aiof:
                await aiof.write("This is ")
                await aiof.write("an async test")

    asyncio.run(async_write_test())
    with open_resource("Test.txt") as f:
        assert f.read_text() == "This is an async test"


@pytest.mark.integration
def test_can_async_source_members_csv(
    async_client,
    current_session_code,
):
    file_name = "Members.csv"
    base_csv_endpoint = f"{FILES_ENDPOINT}/{current_session_code}/"
    asyncio.run(async_download_file(async_client, base_csv_endpoint, file_name))


@pytest.mark.integration
def test_async_can_download_all_files():
    download_all_files()
