import argparse
import os
import select

from socket import *

# parse the request from a client socket
def process_http_header(socket):
    # make a file object using the (client) socket
    # to make use of the file.readline API
    rfile = socket.makefile('rb', -1)
    # get the first line of the request header
    request_line = rfile.readline(65536).rstrip(b'\r\n')
    # split the first line with space
    components = request_line.split()
    # we assume there are 3 words separated by whitespace
    if len(components) != 3:
        print('request line error:{}'.format(request_line))
        return None
    method, uri, version = components

    # to get the header fields line by line
    header_fields = {}
    while True:
        # make use of the file.readline api to read a line from the (clinet) socket
        line = rfile.readline(65536).rstrip(b'\r\n')
        # an empty line indicates the end of the request header
        if line == b'':
            break
        # The first colon split the line into key and value
        components = line.split(b':', maxsplit=1)
        # remove the redundant space around key or value
        k, v = map(lambda x: x.strip(), components)

        header_fields[k] = v
    # return a python string representation of the uri
    return uri.decode()


# send response the to a client socket
def send_response(sock, uri):
    # None indicates wrong format of request header
    if uri is None:
        status, msg = 400, 'BadRequest'
    else:
        # the file path is relative to "static" folder in the same directory
        path = os.path.join('static', uri[1:])

        # when the path exists and points to a file rather than a directory
        if os.path.exists(path) and os.path.isfile(path):
            status, msg = 200, 'Ok'
            with open(path, 'rb') as f:
                data = f.read()
        else:
            status, msg = 404, 'NotFound'
    if status == 200:
        header = 'HTTP/1.1 {} {}\r\n' \
                 'Content-Type: text/html\r\n' \
                 'Content-Length: {}\r\n' \
                 'Connection: close\r\n' \
                 '\r\n'.format(status, msg, len(data))
    else:
        header = 'HTTP/1.1 {} {}\r\n' \
                 'Content-Type: text/html\r\n' \
                 'Connection: close\r\n' \
                 '\r\n'.format(status, msg)
    # send the header
    sock.sendall(header.encode())
    # send the data if necessary
    if status == 200:
        sock.sendall(data)
        sock.close()


# make a http server and run it
def run_server(host, port):
    # make a TCP socket
    server_sock = socket(AF_INET, SOCK_STREAM)
    # bind
    server_sock.bind((host, port))
    # listen, set backlog to 5 which indicates the server would be able to listen 5
    # pending connections
    server_sock.listen(5)
    print('HTTP server is listening on {}:{}...'.format(host, port))
    # the socket set to examine whether ready for reading
    inputs = [server_sock]
    while True:
        # get the readable sockets
        readable, writable, exceptional = select.select(inputs, [], [])
        # iterate all readable sockets
        for sock in readable:
            # when new client connects
            if sock == server_sock:
                client_sock, client_addr = server_sock.accept()
                print("server: got connection %d from %s" % (client_sock.fileno(), client_addr))
                # add the client socket to the examinable (readable) set
                inputs.append(client_sock)
            # when a client socket is ready for reading
            else:
                client_sock = sock
                # get the request uri
                uri = process_http_header(client_sock)
                # send response
                send_response(client_sock, uri)
                # remove the client socket from the examinable set
                inputs.remove(client_sock)
                # close the client socket
                client_sock.close()


if __name__ == '__main__':
    # parse host and port from the commandline
    parser = argparse.ArgumentParser(description='A simple http server using select.')
    parser.add_argument('--host', action="store", dest="host", required=True)
    parser.add_argument('--port', action="store", dest="port", type=int, required=True)
    given_args = parser.parse_args()
    host = given_args.host
    port = given_args.port
    # run server
    run_server(host, port)
