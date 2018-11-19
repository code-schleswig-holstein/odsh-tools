# Datapusher

This skript is intended to be used to create datasets based on data from a spreadsheet file,
that could be either in Excel format (.xls, .xlsx) or CSV format.

In the Initialisation section, first the correct settings of `Host` and `api_key` have to be set.
The `api_key` can be found after login to ckan within the user details section.

The filename of the spreadsheet file as well as its path should be adjusted.
If a connection to ckan can be established, a report file will be created that contains information
about all rows of the spreadsheet file that successfully formed a package, in addition to
errors that were also printed to the console.

Entries for the following fields must already exist in CKAN: `OWNER_ORG` ,`Licence` and `Groups`,
i.e. unknown entries are taken es errors.
