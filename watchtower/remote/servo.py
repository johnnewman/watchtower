from . import micro

class Servo:
    """
    Class used to represent one servo attached to a microcontroller. An
    instance of Servo can be used to tell the microcontroller to move the 
    servo to the on or off position.
    """

    def __init__(self,
                 angle_on: int,
                 angle_off: int):
        
        super(Servo, self).__init__()
        self.__angle_on = angle_on
        self.__angle_off = angle_off

    def enable(self):
        micro.set_angle(self.__angle_on)

    def disable(self):
        micro.set_angle(self.__angle_off)
