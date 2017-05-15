from subprocess import check_output, call
from sys import exit, argv, executable
import re
import os

#There are some assumptions:
# - you run this manually using sudo, or you run this with '--setup' to add
#   as a startup service
# - you have awscli installed
# - you have awscli configured
# - all files you care about have matching IP values (i.e., they are in sync)
# - at least one of those files is a django settings.py project file (because
#   that's where we will get the (potentially) old external IP address)

#Instructions:
# - add all files you wish to keep updated to the 'files_to_update' list below
# - add all the corresponding services to the 'services' list below

#User variables:
files_to_update = []
files_to_update.append("/etc/nginx/nginx.conf")
files_to_update.append("/home/ubuntu/TriggerWarnings/TriggerWarnings/settings.py")
services = []
services.append("gunicorn")
services.append("nginx")

#Edit a file in place, replacing old_string with new_string.
#Returns: 0 on success; >0 on failure
def replace_string_in_file(filename, old_string, new_string):
    try:
        f = open(filename,'r')
        old_data = f.read()
        f.close()
    except IOError:
        return 1

    new_data = old_data.replace(old_string, new_string)

    try:
        f = open(filename,'w')
        f.write(new_data)
        f.close()
    except IOError:
        return 2

    return 0

#Look in a django settings.py project file and grab the IP address
#from the ALLOWED_HOSTS line.
#Returns: "xxx.xxx.xxx.xxx" on success; "" on failure
# Format: ALLOWED_HOSTS = ['xxx.xxx.xxx.xxx']
#     or: ALLOWED_HOSTS = ["xxx.xxx.xxx.xxx"]
def extract_ip_from_settings_file(filename):
    ip = ""
    if not os.path.exists(filename):
        return ip
    try: 
        f = open(filename,'r')
        data = f.read()
        f.close()
    except IOError:
        return ip

    for line in data.split("\n"):
        if "ALLOWED_HOSTS" in line:
            parsed_line = re.split("[\'\"]", line)
            ip = parsed_line[1]
            break
    return ip


rc = 0

#Set script as a "startup" service to automatically run it
#after a reboot/restart.
def setup():
    service_name = __file__.replace(".py","") + ".service"
    service_file = "/etc/systemd/system/" + service_name
    data = """
[Unit]
Description=Check if External IP has changed and update it
After=network.target

[Service]
User=ubuntu
Group=www-data
ExecStart=/usr/bin/sudo %s %s

[Install]
WantedBy=multi-user.target
""" % (executable, os.path.realpath(__file__))

    try:
        f = open(service_file, 'w')
        f.write(data)
        f.close()
    except IOError:
        print "ERROR: unable to create startup service file. Are you using sudo?"
        return 4

    if call("systemctl daemon-reload", shell=True) != 0:
        print "ERROR: error during daemon-reload"
        return 5

    if call("systemctl enable %s" % service_name, shell=True) != 0:
        print "ERROR: error enabling %s" % service_name
        return 6

    if call("systemctl start %s" % service_name, shell=True) != 0:
        print "ERROR: error starting %s" % service_name
        return 7

    print "Created a new service file: %s" % service_file
    print "It references this script: %s" % os.path.realpath(__file__)
    print "If you move the script, update the service file."
    return 0


#Handle setup.
if len(argv) > 1 and argv[1] == "--setup":
    print "Running setup."
    exit(setup())

#Get our internal IP which we will use to get our external IP (this is just one way to do it).
#The expected output of 'ip route get 8.8.8.8' is:
#8.8.8.8 via xxx.xxx.xxx.xxx dev eth0  src yyy.yyy.yyy.yyy
#    cache 
#
#yyy.yyy.yyy.yyy is your internal IP
#
ip_output = check_output("ip route get 8.8.8.8 | awk '{print $NF;exit}'", shell=True)
int_ip = ip_output.replace('\n','')

#Get our CURRENT external IP (this requires awscli to be installed,
# and assumes you have configured it ... and assumes Amazon doesn't change the output).
#This will get ALL of our instances.
all_instances = check_output("aws ec2 describe-instances | grep INSTANCES", shell=True)
#Look for our internal IP and get the matching external IP.
ext_ip = ""
for instance in all_instances.split("\n"):
    if int_ip in instance:
        #The external IP is the 16th field (currently).
        ext_ip = instance.split("\t")[15]
        break

#Check:
if not ext_ip:
    print "ERROR: not able to determine external IP value."
    exit(1)

#Get the (possibly) old external IP value from one of the settings.py files
#since they are easy to parse.
old_ip = ""
for filename in files_to_update:
    if "settings.py" in filename:
        old_ip = extract_ip_from_settings_file(filename)
        if old_ip:
            break

#Check:
if not old_ip:
    print "ERROR: not able to extract IP from any settings.py file."
    exit(2)

#Do we need to update?
#Again, we are assuming that all files have the same IP in them.
if old_ip == ext_ip:
    #We can just exit with success.
    print "No update needed."
    exit(rc)

#Now check each file and replace the old value with the new value.
print "Updating files from %s to %s ..." % (old_ip, ext_ip)
for filename in files_to_update:
    if replace_string_in_file(filename, old_ip, ext_ip) > 0:
        print "ERROR: could not update %s" % filename
    else:
        print "\t%s" % filename

#Restart services.
print "Restarting services ..."
for s in services:
    if call("service %s restart" % s, shell=True) != 0:
        print "ERROR: error restarting %s" % s
        rc = 3
    else:
        print "\t%s" % s

exit(rc)
