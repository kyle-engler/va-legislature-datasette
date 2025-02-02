"""
Downloads the raw daily VA Legislature Information System CSVs and saves them to the package for
creating the dataset. We use an async because its fun.

Determines the latest session number at runtime.
"""

import asyncio
from datetime import datetime
from itertools import product
from urllib.parse import urljoin

import aiofiles
import httpx

from va_legislature_datasette.load import open_resource

VA_LIS_HOST_NAME = "https://lis.blob.core.windows.net/"


FILES_ENDPOINT = urljoin(VA_LIS_HOST_NAME, "lisfiles")


files = [
    "Amendments.csv",
    "BILLS.CSV",
    "CIBillSubjects.csv",
    "CIParentChildSubjects.csv",
    "CommitteeMembers.csv",
    "Committees.csv",
    "DOCKET.CSV",
    "FiscalImpactStatements.csv",
    "HISTORY.CSV",
    "Members.csv",
    "Sponsors.csv",
    "SubCommitteeMembers.csv",
    "SUBDOCKET.CSV",
    "Summaries.csv",
    "VOTE.CSV",
    "VoteStatements.csv",
]


def download_all_files():
    """
    Source all the CSVs from their HTTP endpoints so we can build today dataset!

    .. note::

        We don't need to do this with async tools, but it's a good opportunity
        to learn something new and these libraries are already part of datasette's
        transitive dependency tree, so we're not adding any extra cruft!
    """
    client = httpx.AsyncClient()
    session_id = legislative_session_identifier(FILES_ENDPOINT)

    async def concurrent_runner():
        tasks = (
            async_download_file(client, f"{FILES_ENDPOINT}/{session_id}/", file_name)
            for file_name in files
        )
        await asyncio.gather(*tasks)

    asyncio.run(concurrent_runner())


def legislative_session_identifier(files_endpoint) -> str:
    """
    Sesions are number YYYYN where N is 1-3 depending on the session type

    Poke at the BILLS.CSV url to determine the current session.
    """
    cannary_file = "BILLS.CSV"
    year = datetime.now().year
    # Check in priority order ie (2025, 3), (2025, 2), etc. We also check last year
    # if a new session hasn't started for the current year!
    for year, session_number in tuple(product((year, year - 1), (3, 2, 1))):
        session_code = f"{year}{session_number}"
        response = httpx.head(f"{files_endpoint}/{session_code}/{cannary_file}")
        if response.status_code == httpx.codes.OK:
            return session_code
    else:
        raise ExtractException(
            "Could not determine the session indentifier by checking for the BILLS.CSV file!"
        )


async def async_download_file(client, base_csv_endpoint, url_file_name):
    """Over-engineered async download and package file writer for the fun of it!

    Args:
        client: Async HTTPx client
        base_csv_endpoint: The base url path without the url file name for the session number.
            Example, ``
        url_file_name: The url name of the CSV file. Note the URLs are inconsistently case-sensitive!!!
            For example `BILLS.CSV` versus `Amendments.csv`
    """
    # Conform to lowercase file extensions
    name, extension = url_file_name.split(".")
    with open_resource(f"{name}.{extension.lower()}") as res:
        async with client.stream(
            "GET", urljoin(base_csv_endpoint, url_file_name)
        ) as response:
            response.raise_for_status()

            async with aiofiles.open(res, "wb") as af:
                async for chunk in response.aiter_bytes():
                    await af.write(chunk)


class ExtractException(Exception):
    pass
