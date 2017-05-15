# aws-update-ip
Keep your external IP up to date if your EC2 instance restarts.


There are some assumptions:
 - you run this manually using sudo, or you run this with '--setup' to add as a
   startup service
 - you have awscli installed
 - you have awscli configured
 - all files you care about have matching IP values (i.e., they are in sync)
 - at least one of those files is a django settings.py project file (because
   that's what's used to get the (potentially) old external IP address)

Instructions:
 - add all files you wish to keep updated to the 'files_to_update' list
 - add the corresponding services to the 'services' list


