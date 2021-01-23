# DiSig
## Overview
Disig is a simple digital signage server on the Raspberry Pi.  


## Description
Disig consists of two parts;server side program and client side program, which are connect with each other via socket.io.  

### Server side program
It's written by Python3.
Main roles are to get PDF file from Dropbox and to run the server that provides pdf data to clients.  
This program was tested on Raspberry Pi OS 64bit and Python3.7.3.  


### Client side program
It's written by JavaScript and executed when the browser accesses web server.  
Main roles are to receive PDF data from server and to render it using PDF.js.  
This program was tested on Raspberry Pi OS 64bit and Chrome and Windows10 and Firefox.


## Requirement
- Debian Buster
- python3
- python3-pip

## Install
```bash
git clone https://github.com/seigo2016/Digital-Signage.git
cd Digital-Signage
sudo ./setup.sh
```
### COUTION
You need to put client_secret.json in this root directory.  
When You run main.py first time, you have to do some steps to obtain OAuth 2.0 access tokens.  

## Author
[seigo2016](https://github.com/seigo2016)

## LICENSE
[MIT](./LICENSE)
