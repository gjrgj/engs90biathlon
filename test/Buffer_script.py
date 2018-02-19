def Buffer_Time_minute(IN_FiFo, OUT_Buffer_Time_minute):
    i = 0
    for i in range(len(OUT_Buffer_Time_minute) - 1):
        OUT_Buffer_Time_minute[i] = OUT_Buffer_Time_minute[i + 1]
        i = i + 1
    OUT_Buffer_Time_minute[60] = IN_FiFo

def Buffer_Zg(IN_FiFo, OUT_Buffer_Zg):
    i = 0
    for i in range(len(OUT_Buffer_Zg) - 1):
        OUT_Buffer_Zg[i] = OUT_Buffer_Zg[i + 1]
        i = i + 1
    OUT_Buffer_Zg[60] = IN_FiFo