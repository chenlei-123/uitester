

class Device:
    BLANK = 0x0
    OFFLINE = 0x1
    ONLINE = 0x2
    READY = 0x3
    RUNNING = 0x4

    def __init__(self, device_id):
        self.status = self.BLANK
        self.id = device_id

    def prepare(self):
        pass

class BaseResponseHandler:
    """
    Response handler base class.
    ResponseHandler.handle will be call when receive a RPC-response from client
    """
    def handle(self, device, response):
        pass

