import pyqtgraph as pg


OUT_Buffer_Zg = [5, 5, 5, 5, 5, 5, 5, 8, 8, 8, 8, 5,
    5, 7, 7, 7, 7, 7, 9, 9, 9, 5, 5, 5, 5, 5, 5, 5, 6, 6, 6, 6,
    2, 2, 2, 2, 1, 1, 1, 1, 1, 4, 4, 4, 4, 4, 3, 3, 3, 3, 3, 3,
    6, 6, 6, 6, 0, 0, 0, 0, 0]

OUT_Buffer_Time_minute = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12,
    13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30,
    31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48,
    49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60]


def simple_graph():
    H = pg.plot(OUT_Buffer_Time_minute, OUT_Buffer_Zg, pen='b')
    H.setTitle('Temperature Zgoraj Spodaj')
    H.addLegend()
    H.plot(OUT_Buffer_Time_minute, OUT_Buffer_Zg, pen='r', name='Zg')
    H.showGrid(True, True)
    H.setLabel('left', 'Temperatura', units='deg C')
    H.setLabel('bottom', 'Time', units='minute')