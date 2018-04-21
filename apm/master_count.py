#encoding:utf8
import json
import time

def calc_metrics():
    all_metric = dict()
    s_time = time.time()
    try:
        while True:
            e_time = time.time()
            if e_time - s_time >= 10:
                s_time = e_time
                for i in range(48080,48096):
                    file = open("/usr/local/cdntoolkit/ctk/apm/" + str(i) + ".txt")
                    content = file.read()
                    jd = json.loads(content)
                    for metric, value in jd.items():
                        temp = all_metric.get(metric, None)
                        if temp is None:
                            all_metric[metric] = 0
                        all_metric[metric] += value
                for _metric,_value in all_metric.items():
                    print(_metric, int(_value/10))
                    all_metric[_metric] = 0
                print('------------------------------')
            else:
                time.sleep(0.1)
    except Exception as e:
        print("calc_metrics:", e)


if __name__ == "__main__":
    calc_metrics()
