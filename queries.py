from pymongo import MongoClient
from passlib.context import CryptContext
import datetime
from pprint import pprint
from dateutil import parser


def auth(eid,pwd,db):
    pwd_context = CryptContext(schemes=["sha512_crypt"], 
                           default="sha512_crypt", 
                           sha512_crypt__default_rounds=45000)
    emp = db.employee.find_one({'eid':eid})
    if emp is None:
        return False,"Wrong Eid"
    val = pwd_context.verify(pwd,emp['password'])
    
    if val==False:
        return False,"Wrong Password"
    emp = db.regemployee.find_one({'eid':eid})
    if emp is not None:
        return True,"Regular Employee"
    else:
        return True,"Driver"
    

#create a new booking
def create_new_booking(date,no_people,eid,hiretime,destination,distance,waitingtime,reasonhire,cartype,db):
    if cartype>db.regemployee.find_one({'eid':eid})['Car Type']:
        return "You dont have authorization to book this car type"
    if hiretime<=0:
        return "Hire Time cannot be 0 or less than 0"
    if date<=datetime.datetime.now():
        return "Incorrect Date Time entered"
    car_av = db.cars.find({'Car Type':cartype})
    car_for_booking=0
    for c in car_av:
        if c['No Of Seats']<no_people:
            continue
        flag = True
        for i in range(hiretime):#0 index cause time is one hour is counted as say 11-12 entry has 11
            if (date + datetime.timedelta(hours=date.hour+i) in c['Calendar']):
                flag=False
                break
        if flag==True:
            car_for_booking=c
            break
    
    if car_for_booking==0:
        return "Car not available"
    
    driver_available=0
    for d in db.driver.find():
        flag=True
        for i in range(hiretime):#0 index cause time is one hour is counted as say 11-12 entry has 11
            if (date + datetime.timedelta(hours=date.hour+i) in d['Calendar']):
                flag=False
                break
        if(flag==True):
            driver_available=d
            break
    
    if driver_available==0:
        return "No drivers are available for this time"
    
    #update cars,driver and carhiredb
    for i in range(hiretime):#0 index cause time is one hour is counted as say 11-12 entry has 11
        db.driver.update_one({'eid': driver_available['eid']}, {'$push': {'Calendar':date + datetime.timedelta(hours=i)}})
        db.cars.update_one({'Reg No': car_for_booking['Reg No']}, {'$push': {'Calendar':date + datetime.timedelta(hours=i)}})
        
    car_hire = {'Car Reg No':car_for_booking['Reg No'],
          'Date Time':date,
          'Driver Eid':driver_available['eid'],
          'Employee Eid':eid,
          'Reason of Hire':reasonhire,
          'Fuel Consumed':"",
          'Expenditure':"",
          'Distance':distance,
          'Destination':destination,
          'No of People':no_people,
          'Hire Time':hiretime,
          'Waiting Time':0,
          'Approved':1}
    
    db.carhire.insert_one(car_hire)
    return "Trip Created"




#Find bookings of next n days
def retrive_next_week_booking(eid,day,db):
    booking_next_week=[]
    max_date = datetime.datetime.now().date()+datetime.timedelta(days=day)
    for bk in db.carhire.find({'Employee Eid':eid}):
        bk_date = bk['Date Time'].date()
        if bk_date<=max_date and bk_date>=datetime.datetime.now().date():
            booking_next_week.append(bk)
    
    return booking_next_week


#Cancel booking for a particular date
#display bookings get bkid
def cancel_one_booking(bid,db):
    bk = db.carhire.find_one({'_id':bid})
    for i in range(bk['Hire Time']):
        dt = bk['Date Time']+datetime.timedelta(hours=i)
        db.driver.update_one({'eid':bk['Driver Eid']},{'$pull':{'Calendar':dt}})
        db.cars.update_one({'Reg No':bk['Car Reg No']},{'$pull':{'Calendar':dt}})
    db.carhire.delete_one({'_id':bid})


#increase booking by some time(1hr,2hr,3hr..)
#check if driver is free and car is free
#display all bookings to user and get preferred booking's id
def increase_booking_time(bkid,time,db):
    curbk = db.carhire.find_one({'_id':bkid})
    driver = db.driver.find_one({'eid':curbk['Driver Eid']})
    #check if driver is free
    for i in range(time):#0 index cause time is one hour is counted as say 11-12 entry has 11
        if (curbk['Date Time'] + datetime.timedelta(hours=curbk['Hire Time']+i) in driver['Calendar']):
            return False
           
    #check if car is free
    car = db.cars.find_one({'Reg No':curbk['Car Reg No']})
    for i in range(time):#0 index cause time is one hour is counted as say 11-12 entry has 11
        if (curbk['Date Time'] + datetime.timedelta(hours=curbk['Hire Time']+i) in car['Calendar']):
            return False
    #update carhire,driver and car db
    for i in range(time):#0 index cause time is one hour is counted as say 11-12 entry has 11
        db.driver.update_one({'eid': driver['eid']}, {'$push': {'Calendar':curbk['Date Time'] + datetime.timedelta(hours=curbk['Hire Time']+i)}})
        db.cars.update_one({'Reg No': car['Reg No']}, {'$push': {'Calendar':curbk['Date Time'] + datetime.timedelta(hours=curbk['Hire Time']+i)}})
    
    db.carhire.update_one({'_id': bkid}, {'$set': {'Hire Time':curbk['Hire Time']+time}})
    
    return True


#Find details of current trip
def retrive_cur_trip_details(eid,db):
    details={}
    cur_time = datetime.datetime.now()
    for bk in db.carhire.find({'Employee Eid':eid}):
        bk_date = bk['Date Time'].date()
        hr = []
        for i in range(bk['Hire Time']):
            hr.append(bk['Date Time'].hour + i)
            
        #Get current booking                
        if(bk_date==cur_time.date()) and (cur_time.hour in hr):
        #if True:
            details['Car Reg No'] = bk['Car Reg No']
            
            driver = db.employee.find_one({'eid':bk['Driver Eid']})
            
            if driver['MiddleName']=="":
                details['Driver Name']=driver['FirstName'] + " " + driver['LastName']
            else:
                details['Driver Name']=driver['FirstName'] + " " + driver['MiddleName'] + " " + driver['LastName']
            
            details['Driver Mobile'] = driver['mobile']
    
    return details
