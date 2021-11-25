# Copyright by your friendly neighborhood SaunaLord

Welcome to the unofficial and illegal ASVZ subscriber tool. 
By using this tool the 
["Benutzerordnung für Telematik (BOT)"](https://rechtssammlung.sp.ethz.ch/Dokumente/203.21.pdf) 
of ETH Zürich (at least article 14) is violated and you take full responsibility.
This tool was created solely for research and educational 
purposes.

### How do you use it
1. Clone the repo to your desired folder.
2. Install `geckodriver` for the [selenium](https://selenium-python.readthedocs.io/) library in python
3. Create a key file `key.lock` in the top folder with a random 
key of your desired length
4. Create python virtual environment in the top folder called venv  
`python -m venv .`  
Please use python 3.9 or higher for stability reasons.
5. Enable virtual environment and install requrements  
`source venv/bin/activate`  
`pip install -r requirements.txt`
6. Local testing  
`cd asvzsubscriber`  
`python manage.py makemigrations`  
`python manage.py migrate`  
`python manage.py createsuperuser`  
`python manage.py runserver`  
7. Global setup
   1. Setup gunicorn and nginx  
    For this check out [digitalocean](https://www.digitalocean.com/community/tutorials/how-to-set-up-django-with-postgres-nginx-and-gunicorn-on-debian-10) and search for your operating system
   2. Run scheduled check of events with `timectl`  
    For this check out [systemd-timers](https://opensource.com/article/20/7/systemd-timers)  
   <br>  
        ````
        asvzsubscriber.timer
       
            [Unit]
            Description=ASVZSubscription Check Time.
            Requires=asvzsubscriber.service
       
            [Timer] 
            Unit=asvzsubscriber.service   
            OnCalendar=*-*-* *:2/5:00  
            AccuracySec=10s     
       
            [Install]    
            WantedBy=timers.target 
        ````
        ````
        asvzsubscriber.service
       
            [Unit]
            Description=ASVZ Subscriber
            Wants=asvzsubscriber.timer
    
            [Service]
            Type=simple
            ExecStart=/home/~username~/asvz-subscriber/venv/bin/python /home/~username~/asvz-subscriber/asvzsubscriber/manage.py timecheck
    
            [Install]
            WantedBy=multi-user.target
        ````
   3. Configure your router (*portforwarding* and *dynamic dns name*)  
