class Person:
    """
    Person class definition
    """
    def __init__(self, i, xi, yi):
        self.i = i
        self.x = xi
        self.y = yi
        self.tracks = []

    def getTracks(self):
        return self.tracks

    def getId(self):
        return self.i

    def getX(self):
        return self.x

    def getY(self):
        return self.y

    def updateCoords(self, xn, yn):
        self.tracks.append([self.x, self.y])
        self.x = xn
        self.y = yn

    def resetTracks(self):
        self.tracks = []

    def going_UP(self, line_up):
        return (len(self.tracks) >= 2 and self.tracks[-1][1] <= line_up and self.tracks[-2][1] >= line_up)

    def going_DOWN(self, line_down):
        return (len(self.tracks) >= 2 and self.tracks[-1][1] >= line_down and self.tracks[-2][1] <= line_down)

    def going_RIGHT(self, line_right):
        return (len(self.tracks) >= 2 and self.tracks[-1][0] >= line_right and self.tracks[-2][0] <= line_right)

    def going_LEFT(self, line_left):
        return (len(self.tracks) >= 2 and self.tracks[-1][0] <= line_left and self.tracks[-2][0] >= line_left)