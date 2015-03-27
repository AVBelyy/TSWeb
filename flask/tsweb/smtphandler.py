
import logging, threading

class SMTPHandler(logging.handlers.SMTPHandler):
    """
    Modified logging.handles.SMTPHandler from python. This version supports unicode messages and sends them
    in a separate thread, so that main thread does not block while email is sent.
    """

    def __init__(self, *args, encoding="utf8", **kwargs):
        super(SMTPHandler, self).__init__(*args, **kwargs)

        self.encoding = encoding

    def _send_email(self, msg):
        """
        Function that actually sends emails. Is run in a thread.
        """

        try:
            import smtplib
            port = self.mailport
            if not port:
                port = smtplib.SMTP_PORT
            smtp = smtplib.SMTP(self.mailhost, port, timeout=self.timeout)

            if self.username:
                if self.secure is not None:
                    smtp.ehlo()
                    smtp.starttls(*self.secure)
                    smtp.ehlo()
                smtp.login(self.username, self.password)
            smtp.sendmail(self.fromaddr, self.toaddrs, msg)
            smtp.quit()
        except:
            self.handleError(record)

    def emit(self, record):
        """
        Custom record emission: encode the message and send it in separate thread.
        """

        try:
            from email.utils import formatdate

            msg = self.format(record)
            msg = "From: %s\r\nTo: %s\r\nSubject: %s\r\nDate: %s\r\n\r\n%s" % (
                            self.fromaddr,
                            ",".join(self.toaddrs),
                            self.getSubject(record),
                            formatdate(), msg)

            threading.Thread(target=self._send_email, args=[msg.encode(self.encoding)], daemon=True).start()

        except Exception:
            self.handleError(record)

