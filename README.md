# aws-update-ip
Keep your external IP up to date if your EC2 instance restarts.

I use this for my django projects, since I don't usually leave the
instance(s) running when I'm not actively working on a project. This
script saves me the bother of updating NGINX's conf file and the
django project(s) settings.py file. 

There are some assumptions:
 - you have awscli installed
 - you have awscli configured
 - all files you care about have matching IP values (i.e., they are in sync)
 - at least one of those files is a django settings.py project file (because
   that's what's used to get the (potentially) old external IP address)

Instructions:
 - add all files you wish to keep updated to the 'files_to_update' list
 - add the corresponding services to the 'services' list
 - run this manually using sudo, or run this with '--setup' to add as a
   startup service (if you add it as a service, it will run automatically
   during startup)


