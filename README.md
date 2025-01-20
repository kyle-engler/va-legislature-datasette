# VA Legislature Datasette
## Purpose
To easily open source the raw data provided by the
[Virginia Legislative Information System](https://lis.virginia.gov/home).
- [LIS Data-files](https://lis.virginia.gov/data-files)
- [LIS Data-files Instructions](https://help.lis.virginia.gov/data/index.asp)
## Sourcing raw data
> Use the following URL: https://lis.blob.core.windows.net/lisfiles/, followed by the Session Year,
> Session Type, followed by the name of the CSV file you wish to automatically download.
> 
> For example, if you wish to automatically download the Bills.CSV file for the 2025 Regular Session,
> use the link https://lis.blob.core.windows.net/lisfiles/20251/BILLS.CSV. In this example,
> 2025 represents the Session Year, 1 represents the Regular Session, and BILLS.CSV represents the name of the file.
> Use 2 for a Special Session, and use 3 for a second Special Session.

## Local Developer Install
```cmd
python -m pip install -e . '[dev]'
```
To run the test kit
```cmd
pytest tests.py
```

## Usage
To build the SQLite database after installing the project use the CLI command
```cmd
va-lis
```
This will build the SQLite database!

Then to run the app locally
```cmd
datasette lis.db -o
```
