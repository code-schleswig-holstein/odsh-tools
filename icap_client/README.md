# ICAP CLIENT

The Python-ICAP-Client can be used to call an ICAP-Server with a local file to check if the file
contains any viruses.

Examples:
See odsh_icap_client.py (at the bottom: if __name__ == '__main__'...)
Configuration in odsh_icap_client.cfg -> NEED TO SET THE IPS OF HOST AND CLIENT TO WORK

Contains two test files in the folder 'test_files':
eicar.txt -> standard eicar virus text file (gets detected by the virus scan)
lorem-ipsum.pdf -> one-page-pdf-file containing of text from lorem ipsum, no virus will be detected