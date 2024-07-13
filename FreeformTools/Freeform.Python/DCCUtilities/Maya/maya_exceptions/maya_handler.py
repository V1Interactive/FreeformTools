'''
Freeform Rigging and Animation Tools
Copyright (C) 2020  Micah Zahm

Freeform Rigging and Animation Tools is free software: you can redistribute it 
and/or modify it under the terms of the GNU General Public License as published 
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Freeform Rigging and Animation Tools is distributed in the hope that it will 
be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Freeform Rigging and Animation Tools.  
If not, see <https://www.gnu.org/licenses/>.
'''

import traceback

import smtplib
from email.mime.text import MIMEText

import v1_core


def except_hook(type_, exception, trace):
    '''
    Reports errors to interested parties and prints them to the console.

    TODO: Logging into V1 email is unsecure and google won't allow it, need a different way to send error emails

    Args:
        type (type): Exact type of Exception
        exception (Exception): Exception object
        trace (traceback): Stack trace of the exception
    '''
    formatted_trace = ''.join(traceback.format_tb(trace))
    exception_title = "Exception: {}, {}".format(type_.__name__, exception)
    exception_text = "{}\n{}".format(exception_title, formatted_trace)

    v1_core.v1_logging.get_logger().error("################### V1 STACK ###################")
    if v1_core.exceptions.run_exception_fixes(exception_text):
        v1_core.v1_logging.get_logger().error("################# FIX APPLIED ##################")
    v1_core.v1_logging.get_logger().error(exception_text)
    v1_core.v1_logging.get_logger().error("################# END V1 STACK #################")

    #msg = MIMEText(exception_text)

    #msg['Subject'] = exception_title
    #msg['From'] = "micahz@v1interactive.com"
    #msg['To'] = "micahz@v1interactive.com"

    ## Send the message via our own SMTP server, but don't include the
    ## envelope header.
    #import smtplib
    #server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    #server.ehlo()
    #server.login(username, password)
    #server.sendmail("micahz@v1interactive.com", ["micahz@v1interactive.com"], "TEST")
    #server.quit()