import simplejson,os, json
from apscheduler.schedulers.background import BackgroundScheduler
from multiprocessing.pool import ThreadPool
import time, datetime
import logging, multiprocessing
logging.basicConfig()
from qrmobservium.common.utility import execute_cmd

JOBDIR = "/opt/observium/qrmobservium/common/scheduler/jobs/livedata"
d_time = 0
class SchedulerCollectData():
    def __init__(self, exe_function, live_freq, history_freq):
        # ex: {"4":{"ports":[280,281],"mempools":[1,2]}}
        # {"4":{"ports":[280,281]}}
        self.live_dev = {}#{1:{'devices':[{'device_id':1}]}, 2:{'devices':[{'device_id':2}]}} #{d1:{rec_message}, d2:{rec_message}}
        self.all_dev = {}#{4:{'devices':[{'device_id':4, 'result':0}]}, 5:{'devices':[{'device_id':5, 'result':0}]},6:{'devices':[{'device_id':6, 'result':0}]}, 7:{'devices':[{'device_id':7, 'result':0}]}} # {d1:{rec_message}, d2:{rec_message}}
        self.event_dev = {}
        self.scheduler = BackgroundScheduler({'apscheduler.executors.default': {'class': 'apscheduler.executors.pool:ThreadPoolExecutor','max_workers': '30'}})
        self.exe_function = exe_function
        self.pool = ThreadPool(processes=multiprocessing.cpu_count())
        self.live_freq = int(live_freq)
        self.history_freq = int(history_freq)
        self.send_live = {}
        self.jobdir = '/opt/observium/qrmobservium/common/scheduler/jobs/livedata'
        self.scheduler.add_job(self._period_function, trigger = 'interval', args =('live',), seconds = live_freq, id = "live_period")
        self.scheduler.add_job(self._job_function, trigger = 'interval', args =('job',), seconds = 3, id = "job_poll")
        self.scheduler.start()

    def start(self):
        try:
            # This is here to simulate application activity (which keeps the main thread alive).
            while True:
                time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            self.scheduler.shutdown()  # Not strictly necessary if daemonic mode is enabled but should be done if possible

    def add_dev(self, msg):
        #msg = {"4":{"ports":[280,281]}}
        for dev_id in msg:
            print 'add_dev : %s' % dev_id
            if dev_id not in self.live_dev:
                self.live_dev[dev_id] = msg[dev_id].copy()
                print 'live_list %s' % self.live_dev
        #dev_id = int(msg['devices'][0]['device_id'])
        #if dev_id not in self.live_dev:
        #    msg.pop('get_event_devices', None)
        #    self.all_dev[dev_id] = msg.copy()
        #print "all list:" + simplejson.dumps(self.all_dev)

    def remove_dev(self, msg):
        dev_id = int(msg['devices'][0]['device_id'])
        self.all_dev.pop(dev_id, None)
        self.live_dev.pop(dev_id, None)
        self.event_dev.pop(dev_id, None)

    def add_event_dev(self, msg):
        self.event_dev = {}
        for dev in msg["devices"]:
            self.event_dev[dev["device_id"]] = dev
        #print "event list:" + simplejson.dumps(self.event_dev)

    def remove_event_dev(self, msg):
        dev_id = int(msg['devices'][0]['device_id'])
        self.event_dev.pop(dev_id, None)

    def _period_function(self, schedule_type):
        global d_time
        results = []
        print 'debug %s' % multiprocessing.cpu_count()
        if schedule_type == "live":
            #print "enter live_function:" + str(datetime.datetime.now())
            d_time = int(time.time())
            for key, value in self.live_dev.iteritems():
                print '_period %s %s d_time %s' % (key, value, d_time)
            #value =self.live_dev.values()
                for port_id in value['ports']:
                    #print 'kk %s' % port_id
                    self.pool.apply_async(self.exe_function, args = (key, port_id,))
                
    def _job_function(self, schedule_type):
        if not os.path.isdir(self.jobdir):
            print 'path not exist'
            return
        device_ids = os.listdir(self.jobdir)
        if len(device_ids) <= 0:
            print 'no devices'
            for device_id in self.live_dev.keys():
                for port in self.live_dev[device_id]['ports']:
                    self.live_dev[device_id]['ports'].remove(port)
                del self.live_dev[device_id]
            return
        for device_id in self.live_dev.keys():
            if device_id not in device_ids:
                self.live_dev.pop(device_id, None);
        for device_id in device_ids:
            msg = {}
            constructport = {}
            portlist = []
            ports = os.listdir(self.jobdir + "/" + device_id)
            if len(ports) <= 0:
                if not device_id in self.live_dev:
                    return
                for port in self.live_dev[device_id]['ports']:
                    if port not in ports:
                        self.live_dev[device_id]['ports'].remove(port)
                        print 'del ports %s' % self.live_dev[device_id]['ports']
                return
            portlist = [int(port) for port in ports]
            #msg[device_id] = constructport
            if device_id in self.live_dev:
                cur_ports = self.live_dev[device_id]['ports']
            else:
                cur_ports = []
            diff_ports = list(set(portlist) - set(cur_ports)) 
            if len(diff_ports) == 0 and len(portlist) >= len(cur_ports):
                continue
            for port in diff_ports:
                if port not in portlist:
                    portlist.append(port)
            constructport['ports'] = portlist
            msg[device_id] = constructport
            self.live_dev[device_id] = msg[device_id].copy()
            print '_job_function live_list %s' % self.live_dev

    def change_live_freq(self, sec):
        self.live_freq = sec
        self.scheduler.reschedule_job(job_id="live_period" ,trigger='interval', seconds=self.live_freq)

    def change_history_freq(self, minute):
        self.history_freq = minute
    
def exe_function(device_id, port_id):
    global d_time
    print "exe_function %s %s" % (device_id , port_id)
    data = {}
    cmd = "/usr/bin/php /opt/observium/customdata.php {} {}".format(device_id, port_id)
    ret = execute_cmd(cmd).split('\n')[0]
    print ret
    try:
        with open( JOBDIR + "/" + device_id + "/" + "%s" % port_id , 'r') as f:
            data = json.load(f)
            data['last_in'] = data['if_in']
            data['last_out'] = data['if_out']
            data['last_time'] = data['current_time']
    except ValueError:
        print 'Decoding JSON has failed'
    data['if_in'] = ret.split('|')[1]
    data['if_out'] = ret.split('|')[2]
    data['current_time'] = int(time.time())
    with open( JOBDIR + "/" + device_id + "/" + "%s" % port_id , 'w') as f:
        json.dump(data, f)
    print 'execuation time %s' % (int(time.time()-d_time))

t = SchedulerCollectData(exe_function, 15, 5)
t.add_dev({"4":{"ports":[281,282]}})
t.start()
#t.add_dev({'devices':[{'device_id':4, 'result':0}]})
#t.start()
#t.long_period_function()
