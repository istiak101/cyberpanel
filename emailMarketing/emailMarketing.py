#!/usr/local/CyberCP/bin/python

import os
import time
import csv
import re
import plogical.CyberCPLogFileWriter as logging
from .models import EmailMarketing, EmailLists, EmailsInList, EmailTemplate, EmailJobs, SMTPHosts
from websiteFunctions.models import Websites
import threading as multi
import socket, smtplib
import DNS
from random import randint
from plogical.processUtilities import ProcessUtilities

class emailMarketing(multi.Thread):
    def __init__(self, function, extraArgs):
        multi.Thread.__init__(self)
        self.function = function
        self.extraArgs = extraArgs

    def run(self):
        try:
            if self.function == 'createEmailList':
                self.createEmailList()
            elif self.function == 'verificationJob':
                self.verificationJob()
            elif self.function == 'startEmailJob':
                self.startEmailJob()
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + ' [emailMarketing.run]')

    def createEmailList(self):
        try:
            website = Websites.objects.get(domain=self.extraArgs['domain'])
            try:
                newList = EmailLists(owner=website, listName=self.extraArgs['listName'], dateCreated=time.strftime("%I-%M-%S-%a-%b-%Y"))
                newList.save()
            except:
                newList = EmailLists.objects.get(listName=self.extraArgs['listName'])

            counter = 0

            if self.extraArgs['path'].endswith('.csv'):
                with open(self.extraArgs['path'], 'r') as emailsList:
                    data = csv.reader(emailsList, delimiter=',')
                    for items in data:
                        try:
                            for value in items:
                                if re.match('^[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,4})$', value) != None:
                                    try:
                                        getEmail = EmailsInList.objects.get(owner=newList, email=value)
                                    except:
                                        newEmail = EmailsInList(owner=newList, email=value,
                                                                verificationStatus='NOT CHECKED',
                                                                dateCreated=time.strftime("%I-%M-%S-%a-%b-%Y"))
                                        newEmail.save()
                                    logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'], str(counter) + ' emails read.')
                                    counter = counter + 1
                        except BaseException as msg:
                            logging.CyberCPLogFileWriter.writeToFile(str(msg))
                            continue
            elif self.extraArgs['path'].endswith('.txt'):
                with open(self.extraArgs['path'], 'r') as emailsList:
                    emails = emailsList.readline()
                    while emails:
                        email = emails.strip('\n')
                        if re.match('^[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,4})$', email) != None:
                            try:
                                getEmail = EmailsInList.objects.get(owner=newList, email=email)
                            except BaseException as msg:
                                newEmail = EmailsInList(owner=newList, email=email, verificationStatus='NOT CHECKED',
                                                        dateCreated=time.strftime("%I-%M-%S-%a-%b-%Y"))
                                newEmail.save()
                            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'],str(counter) + ' emails read.')
                            counter = counter + 1
                        emails = emailsList.readline()

            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'], str(counter) + 'Successfully read all emails. [200]')
        except BaseException as msg:
            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'], str(msg) +'. [404]')
            return 0

    def findNextIP(self):
        try:
            if self.delayData['rotation'] == 'Disable':
                return None
            elif self.delayData['rotation'] == 'IPv4':
                if self.delayData['ipv4'].find(',') == -1:
                    return self.delayData['ipv4']
                else:
                    ipv4s = self.delayData['ipv4'].split(',')

                    if self.currentIP == '':
                        return ipv4s[0]
                    else:
                        returnCheck = 0

                        for items in ipv4s:
                            if returnCheck == 1:
                                return items
                            if items == self.currentIP:
                                returnCheck = 1

                        return ipv4s[0]
            else:
                if self.delayData['ipv6'].find(',') == -1:
                    return self.delayData['ipv6']
                else:
                    ipv6 = self.delayData['ipv6'].split(',')

                    if self.currentIP == '':
                        return ipv6[0]
                    else:
                        returnCheck = 0

                        for items in ipv6:
                            if returnCheck == 1:
                                return items
                            if items == self.currentIP:
                                returnCheck = 1
                    return ipv6[0]
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return None

    def verificationJob(self):
        try:

            verificationList = EmailLists.objects.get(listName=self.extraArgs['listName'])
            domain = verificationList.owner.domain


            if not os.path.exists('/home/cyberpanel/' + domain):
                os.mkdir('/home/cyberpanel/' + domain)

            tempStatusPath = '/home/cyberpanel/' + domain + "/" + self.extraArgs['listName']
            logging.CyberCPLogFileWriter.statusWriter(tempStatusPath, 'Starting verification job..')

            counter = 1
            allEmailsInList = verificationList.emailsinlist_set.all()

            configureVerifyPath = '/home/cyberpanel/configureVerify'
            finalPath = '%s/%s' % (configureVerifyPath, domain)

            counterGlobal = 0

            import json
            if os.path.exists(finalPath):
                self.delayData = json.loads(open(finalPath, 'r').read())

            self.currentIP = ''

            for items in allEmailsInList:
                if items.verificationStatus != 'Verified':
                    try:
                        email = items.email
                        domainName = email.split('@')[1]
                        records = DNS.dnslookup(domainName, 'MX')

                        for mxRecord in records:
                            # Get local server hostname
                            host = socket.gethostname()

                            if os.path.exists(finalPath):
                                try:
                                    logging.CyberCPLogFileWriter.writeToFile('Checking if delay is enabled for verification..')
                                    delay = self.delayData['delay']
                                    if delay == 'Enable':
                                        logging.CyberCPLogFileWriter.writeToFile(
                                            'It seems delay is enabled...')
                                        if counterGlobal == int(self.delayData['delayAfter']):
                                            logging.CyberCPLogFileWriter.writeToFile(
                                                'Sleeping for %s seconds...' % (self.delayData['delayTime']))
                                            time.sleep(int(self.delayData['delayTime']))
                                            counterGlobal = 0
                                            self.currentIP = self.findNextIP()

                                            logging.CyberCPLogFileWriter.writeToFile(
                                                'IP in use: %s.' % (str(self.currentIP)))

                                            if self.currentIP == None:
                                                server = smtplib.SMTP()
                                            else:
                                                server = smtplib.SMTP(self.currentIP)
                                        else:

                                            if self.currentIP == '':
                                                self.currentIP = self.findNextIP()

                                            logging.CyberCPLogFileWriter.writeToFile(
                                                'IP in use: %s.' % (str(self.currentIP)))

                                            if self.currentIP == None:
                                                server = smtplib.SMTP()
                                            else:
                                                server = smtplib.SMTP(self.currentIP)
                                    else:
                                        logging.CyberCPLogFileWriter.writeToFile(
                                            'Delay not configured..')
                                        server = smtplib.SMTP()
                                except BaseException as msg:
                                    logging.CyberCPLogFileWriter.writeToFile(
                                        'Delay not configured.. Error: %s' % (str(msg)))
                                    server = smtplib.SMTP()
                            else:
                                logging.CyberCPLogFileWriter.writeToFile(
                                    'Delay not configured..')
                                server = smtplib.SMTP()


                            server.set_debuglevel(0)

                            # SMTP Conversation
                            server.connect(mxRecord[1])
                            server.helo(host)
                            server.mail('host' + "@" + host)
                            code, message = server.rcpt(str(email))
                            server.quit()

                            # Assume 250 as Success
                            if code == 250:
                                items.verificationStatus = 'Verified'
                                items.save()
                                break
                            else:
                                items.verificationStatus = 'Verification Failed'
                                logging.CyberCPLogFileWriter.writeToFile(email + " verification failed with error: " + message.decode())
                                items.save()

                        logging.CyberCPLogFileWriter.statusWriter(tempStatusPath, str(counter) + ' emails verified so far..')
                        counter = counter + 1
                    except BaseException as msg:
                        items.verificationStatus = 'Verification Failed'
                        items.save()
                        counter = counter + 1
                        logging.CyberCPLogFileWriter.writeToFile(str(msg))


                    counterGlobal = counterGlobal + 1

            logging.CyberCPLogFileWriter.statusWriter(tempStatusPath, str(counter) + ' emails successfully verified. [200]')
        except BaseException as msg:
            verificationList = EmailLists.objects.get(listName=self.extraArgs['listName'])
            domain = verificationList.owner.domain
            tempStatusPath = '/home/cyberpanel/' + domain + "/" + self.extraArgs['listName']
            logging.CyberCPLogFileWriter.statusWriter(tempStatusPath, str(msg) +'. [404]')
            logging.CyberCPLogFileWriter.writeToFile('your error')
            return 0

    def startEmailJob(self):
        try:
            try:
                if self.extraArgs['host'] == 'localhost':
                    smtpServer = smtplib.SMTP('127.0.0.1')
                else:
                    verifyHost = SMTPHosts.objects.get(host=self.extraArgs['host'])
                    smtpServer = smtplib.SMTP(str(verifyHost.host), int(verifyHost.port))
                    smtpServer.login(str(verifyHost.userName), str(verifyHost.password))
            except smtplib.SMTPHeloError:
                logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'],
                                                          'The server didnt reply properly to the HELO greeting.')
                return
            except smtplib.SMTPAuthenticationError:
                logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'],
                                                          'Username and password combination not accepted.')
                return
            except smtplib.SMTPException:
                logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'],
                                                          'No suitable authentication method was found.')
                return

            emailList = EmailLists.objects.get(listName=self.extraArgs['listName'])
            allEmails = emailList.emailsinlist_set.all()
            emailMessage = EmailTemplate.objects.get(name=self.extraArgs['selectedTemplate'])

            totalEmails = allEmails.count()
            sent = 0
            failed = 0

            ipFile = "/etc/cyberpanel/machineIP"
            f = open(ipFile)
            ipData = f.read()
            ipAddress = ipData.split('\n', 1)[0]

            ## Compose Message
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText
            import re

            tempPath = "/home/cyberpanel/" + str(randint(1000, 9999))

            emailJob = EmailJobs(owner=emailMessage, date=time.strftime("%I-%M-%S-%a-%b-%Y"),
                                 host=self.extraArgs['host'], totalEmails=totalEmails,
                                 sent=sent, failed=failed
                                 )
            emailJob.save()

            for items in allEmails:
                try:
                    message = MIMEMultipart('alternative')
                    message['Subject'] = emailMessage.subject
                    message['From'] = emailMessage.fromEmail
                    message['reply-to'] = emailMessage.replyTo

                    if (items.verificationStatus == 'Verified' or self.extraArgs[
                        'verificationCheck']) and not items.verificationStatus == 'REMOVED':
                        try:

                            removalLink = "https:\/\/" + ipAddress + ":8090\/emailMarketing\/remove\/" + self.extraArgs[
                                'listName'] + "\/" + items.email
                            messageText = emailMessage.emailMessage.encode('utf-8', 'replace')
                            message['To'] = items.email

                            if re.search(b'<html', messageText, re.IGNORECASE) and re.search(b'<body', messageText,
                                                                                             re.IGNORECASE):
                                finalMessage = messageText.decode()

                                self.extraArgs['unsubscribeCheck'] = 0
                                if self.extraArgs['unsubscribeCheck']:
                                    messageFile = open(tempPath, 'w')
                                    messageFile.write(finalMessage)
                                    messageFile.close()

                                    command = "sudo sed -i 's/{{ unsubscribeCheck }}/" + removalLink + "/g' " + tempPath
                                    ProcessUtilities.executioner(command, 'cyberpanel')

                                    messageFile = open(tempPath, 'r')
                                    finalMessage = messageFile.read()
                                    messageFile.close()

                                html = MIMEText(finalMessage, 'html')
                                message.attach(html)

                            else:
                                finalMessage = messageText

                                if self.extraArgs['unsubscribeCheck']:
                                    finalMessage = finalMessage.replace('{{ unsubscribeCheck }}', removalLink)

                                html = MIMEText(finalMessage, 'plain')
                                message.attach(html)

                            smtpServer.sendmail(message['From'], items.email, message.as_string())
                            sent = sent + 1
                            emailJob.sent = sent
                            emailJob.save()
                            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'],
                                                                      'Successfully sent: ' + str(
                                                                          sent) + ' Failed: ' + str(
                                                                          failed))
                        except BaseException as msg:
                            failed = failed + 1
                            emailJob.failed = failed
                            emailJob.save()
                            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'],
                                                                      'Successfully sent: ' + str(
                                                                          sent) + ', Failed: ' + str(failed))
                            logging.CyberCPLogFileWriter.writeToFile(str(msg))
                except BaseException as msg:
                            failed = failed + 1
                            emailJob.failed = failed
                            emailJob.save()
                            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'],
                                                                      'Successfully sent: ' + str(
                                                                          sent) + ', Failed: ' + str(failed))
                            logging.CyberCPLogFileWriter.writeToFile(str(msg))


            emailJob = EmailJobs(owner=emailMessage, date=time.strftime("%I-%M-%S-%a-%b-%Y"),
                                 host=self.extraArgs['host'], totalEmails=totalEmails,
                                 sent=sent, failed=failed
                                 )
            emailJob.save()

            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'],
                                                      'Email job completed. [200]')
        except BaseException as msg:
            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'], str(msg) + '. [404]')
            return 0