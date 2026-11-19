class EmailService:
    def __init__(self, log):
        self.log = log

    def send_welcome(self, user):
        self.log.info('Welcome email queued for user id=%s', user.id)
