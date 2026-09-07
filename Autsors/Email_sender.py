from email import encoders
import smtplib
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate
import mimetypes


class EmailConnector:
    def __init__(self, to_addr, text, encode='utf-8', subject='MES рассылка'):
        self.subject = subject
        self.text = text
        self.to_addr = to_addr
        self.from_addr =  'mes_informer@powerz.ru' # 'gas53@internet.ru'  
        self.server = 'mail.powerz.ru' #  'smtp.powerz.ru'
        self.port =  25 #  25 995
        self.passwd = 'Wbw4SrwciU7baSdo7wzi8qSkGm8vVCSc' #'HMsT7n7w7cUHvUHgBS92'  
        self.encode = 'utf-8'

        charset = f'Content-Type: text/plain; charset={encode}'
        mime = 'MIME-Version: 1.0'
        self.body = "\r\n".join((f"From: {self.from_addr}", f"To: {', '.join(to_addr)}", 
            f"Subject: {self.subject}", mime, charset, "", self.text))

    def run(self, file, is_many_files=False):
        msg = MIMEMultipart()
        msg["From"] = self.from_addr
        msg["Subject"] = self.subject
        msg["Date"] = formatdate(localtime=True)
        if self.text:
            msg.attach(MIMEText(self.text)) # текст письма отправляем как вложение
        msg["To"] = ', '.join(self.to_addr)

        if file:
            attachment = MIMEBase('application', "octet-stream")
            header = 'Content-Disposition' 
            # try:
            if is_many_files:
                for fl in file:
                    ctype, _ = mimetypes.guess_type(fl[0])
                    if not ctype:
                        ctype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    a, b = ctype.split('/', 1)
                    part = MIMEBase(a, b)
                    part.set_payload(fl[1])
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', 'attachment', filename=fl[0])
                    msg.attach(part)

            else:
                header = 'Content-Disposition', f'attachment; filename="{file.filename}"'
                attachment.set_payload(file.file.read())
                attachment.add_header(*header)
                encoders.encode_base64(attachment)
                msg.attach(attachment)
            # except IOError:
            #     print(f"Ошибка при открытии файла вложения {file.filename}")

        try:
            smtp = smtplib.SMTP(self.server, self.port)
            smtp.starttls()
            smtp.ehlo()
            smtp.login(self.from_addr, self.passwd)
            smtp.sendmail(self.from_addr, self.to_addr, msg.as_string())  # текст + вложение
        except smtplib.SMTPException as err:
            print('отправка не удалась')
            raise ValueError('ошибка отправки')
        finally:
            smtp.quit()

# все ошибки отлавливаюстя в главном файле