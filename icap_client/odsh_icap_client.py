import socket
import sys
import time
import ConfigParser


class ODSHICAPRequest(object):

    def __init__(self, FILENAME, cfg_file='odsh_icap_client.cfg'):
        config = ConfigParser.ConfigParser()
        config.read(cfg_file)
        self.HOST = config.get('DEFAULT', 'host')
        self.PORT = int(config.get('DEFAULT', 'port'))
        self.CLIENTIP = config.get('DEFAULT', 'clientip')
        self.FILENAME = FILENAME

    def send(self):
        print("----- Starting ICAP-Request via RESPMOD -----")

        # socket connect
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except socket.error as msg:
            sys.stderr.write("[ERROR] %s\n" % msg[1])
            sys.exit(1)

        try:
            sock.connect((self.HOST, self.PORT))
        except socket.error as msg:
            sys.stderr.write("[ERROR] %s\n" % msg[1])
            sys.exit(2)

        # create and send header
        header = self._get_icap_header(self.FILENAME, self.HOST, self.PORT, self.CLIENTIP).encode()
        sock.send(header)

        # send file and terminating signal
        self._sendfile(self.FILENAME, sock)
        sock.send('0\r\n\r\n')

        # fetch and parse the response
        data_response = self._recvall(sock)
        response_object = self._parse_response(data_response)

        print("----- Finished ICAP-Request via RESPMOD -----")

        return response_object

    def _get_icap_header(self, fileName, host, port, clientIP):
        uniqueInt = time.time() # used to generate "unique" int for disabling cache
    
        icapRequest = 'RESPMOD' + ' ' + 'icap://' + host + ':' + str(port) + '/RESPMOD' + \
                      ' ICAP/1.0\r\n' + 'Host: ' + host + ':' + str(port) + '\r\n'
        icapRequest += 'Allow: 204\r\n'
        icapRequest += 'X-Client-IP: ' + clientIP + '\r\n'
    
        httpRequest = "GET http://" + clientIP + "/" + str(uniqueInt).replace('.', '_') + "/" + \
                      fileName + ' HTTP/1.1\r\nHost: ' + clientIP + '\r\n\r\n'

        httpResponse = 'HTTP/1.1 200 OK\r\n'
        httpResponse += 'Transfer-Encoding: chunked\r\n'
        httpResponse += '\r\n'

        httpRequestLength = len(httpRequest)
        httpResponseLength = len(httpResponse)

        icapRequest += 'Encapsulated: req-hdr=0, res-hdr=' + str(httpRequestLength) + ', res-body=' + \
                       str(httpRequestLength + httpResponseLength) + '\r\n\r\n' + httpRequest + httpResponse;

        return icapRequest

    def _sendfile(self, fileName, sock):
        print('start sending file')
        PACK_SIZE = 1024 # in bytes
    
        with open(fileName) as f:
            l = f.read(PACK_SIZE)
            while(l):
                print('sending %d bytes of data...' % len(l))
                sock.send('{:02X}'.format(len(l)).encode())
                sock.send("\r\n".encode())
                sock.send(l)
                sock.send("\r\n".encode())
                l = f.read(PACK_SIZE)
        print('done sending')
    
    def _recvall(self, sock):
        print('receiving response from icap server')
        BUFF_SIZE = 4096 # 4 KiB
        data = b''
        while True:
            part = sock.recv(BUFF_SIZE)
            data += part
            if len(part) < BUFF_SIZE:
                # either 0 or end of data
                break
        return data

    def _parse_response(self, data_response):
        print('parsing response')
        lines = data_response.split('\r\n')
        http_status_code = self._parse_response_http_statuscode(lines)
        http_block = self._parse_block(lines, 'HTTP/1.1')
        icap_block = self._parse_block(lines, 'ICAP/1.0')

        response_object = ODSHParsedICAPResponse(data_response, http_status_code, http_block, icap_block)
        return response_object

    def _parse_response_http_statuscode(self, data_response_lines):
        http_status_code_found = False
        http_status_code = None
        for line in data_response_lines:
            if line.startswith('HTTP/1.1'):
                http_status_code = int(line.split(' ')[1]) # example: HTTP/1.1 403 VirusFound
                http_status_code_found = True
        
        if not http_status_code_found:
            http_status_code = 200 # if no virus is found, no http_status_code is given, defaulting to 200 OK
        
        return http_status_code

    def _parse_block(self, data_response_lines, block_start_signal):
        block_data = None
        in_block = False

        for line in data_response_lines:
            if line.startswith(block_start_signal):
                in_block = True
                block_data = ''
            if in_block and not len(line):
                in_block = False
                break
            if in_block:
                block_data += line + '\r\n'

        return block_data
            

class ODSHParsedICAPResponse(object):

    def __init__(self, full_response, http_status_code, http_block, icap_block):
        self.full_response = full_response
        self.http_status_code = http_status_code
        self.http_block = http_block
        self.icap_block = icap_block

    def virus_found(self):
        if (self.http_status_code != 200) and (self.http_status_code != 403):
            raise UnknownResponseException('Received an unknown http response code: %d' % self.http_status_code)
        return self.http_status_code != 200


class UnknownResponseException(Exception):
    pass
    

def example_print_response(response_object):
    print('')
    print('Example output of response_object:')
    print('')

    #print('Full ICAP-Response: ')
    #print(response_object.full_response)
    #print('')

    print('HTTP-Status-Code (explicit or implied):')
    print(response_object.http_status_code)
    print('')
    
    print('HTTP-Block:')
    print(response_object.http_block)
    print('')

    print('ICAP-Block:')
    print(response_object.icap_block)
    print('')

    print('Virus found?')
    print(response_object.virus_found())
    print('')

        
if __name__ == "__main__":

    # example file with virus
    FILENAME = 'test_files/eicar.txt'

    # example file without virus
    #FILENAME = 'test_files/lorem-ipsum.pdf'

    odsh_parsed_icap_response = ODSHICAPRequest(FILENAME).send()
    example_print_response(odsh_parsed_icap_response)
