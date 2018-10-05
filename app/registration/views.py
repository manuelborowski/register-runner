# -*- coding: utf-8 -*-
# app/asset/views.py

from flask import render_template, redirect, url_for, request, flash, send_file, session, jsonify
from flask_login import login_required, current_user

from .. import db, log
from . import registration
from ..models import  Registration, Series

from ..base import build_filter, get_ajax_table
from ..tables_config import  tables_configuration

import cStringIO, csv, re, datetime

from sqlalchemy.exc import IntegrityError

#This route is called by an ajax call on the assets-page to populate the table.
@registration.route('/registration/data', methods=['GET', 'POST'])
@login_required
def source_data():
    return get_ajax_table(tables_configuration['registration'])

#show a list of registrations
@registration.route('/registration/registrations', methods=['GET', 'POST'])
@login_required
def registrations():
    #The following line is required only to build the filter-fields on the page.
    _filter, _filter_form, a,b, c = build_filter(tables_configuration['registration'])
    return render_template('base_multiple_items.html',
                           title='registraties',
                           filter=_filter, filter_form=_filter_form,
                           config = tables_configuration['registration'])

#start timer
@registration.route('/registration/start/<int:id>', methods=['GET', 'POST'])
@login_required
def start(id):
    try:
        series = Series.query.get(id)
        if not series.running:
            series.running = True
            series.starttime = datetime.datetime.now()
            db.session.commit()
    except Exception as e:
        log.error('cannot start timer of series : {} error {}'.format(series.name, e))
    return jsonify('ok')

#stop timer
@registration.route('/registration/reset/<int:id>', methods=['GET', 'POST'])
@login_required
def reset(id):
    try:
        series = Series.query.get(id)
        series.running = False
        db.session.commit()
    except Exception as e:
        log.error('cannot start/stop timer of series : {} error {}'.format(series.name, e))
    return jsonify('ok')



#Get the timer values for the different series
@registration.route('/registration/get_timer', methods=['GET', 'POST'])
@login_required
def get_timer():
    t = {}
    series = Series.query.order_by(Series.sequence).all()
    nw = datetime.datetime.now()
    for s in series:
        if s.running:
            d = (nw - s.starttime)
            m  = int(d.seconds/60)
            sec = d.seconds - m * 60 + 1
            if d.days < 0:
                m = 0
                sec = 1
            if sec > 59:
                m += 1
                sec = 0
            t[s.id] = '{:02d}:{:02d}'.format(m, sec)
        else:
            t[s.id] = '00:00'
    return jsonify(t)





#give a student a new rfid code
@registration.route('/registration/new_rfid/<int:id>/<string:result>', methods=['GET', 'POST'])
@login_required
def new_rfid(id, result):
    try:
        is_rfid_code, code = decode_code(result)
        if is_rfid_code:
            registration = Registration.query.get(id)
            registration.rfidcode2 = code
            db.session.commit()
    except Exception as e:
        flash('Kan nieuwe RFID niet opslaan')
        log.error('cannot update rfid code: {}'.format(e))

    _filter, _filter_form, a,b, c = build_filter(tables_configuration['registration'])
    return render_template('base_multiple_items.html',
                           title='registraties',
                           filter=_filter, filter_form=_filter_form,
                           config = tables_configuration['registration'])

#delete the rfid code of a student
@registration.route('/registration/delete_rfid/<int:id>', methods=['GET', 'POST'])
@login_required
def delete_rfid(id):
    try:
        registration = Registration.query.get(id)
        registration.rfidcode2 = None
        db.session.commit()
    except Exception as e:
        flash('Kan RFID niet verwijderen')
        log.error('cannot delete rfid code: {}'.format(e))

    _filter, _filter_form, a,b, c = build_filter(tables_configuration['registration'])
    return render_template('base_multiple_items.html',
                           title='registraties',
                           filter=_filter, filter_form=_filter_form,
                           config = tables_configuration['registration'])

def decode_code(code):
    def decode_caps_lock(code):
        out = u''
        dd = {u'&': '1', u'É': '2', u'"': '3', u'\'': '4', u'(': '5', u'§': '6', u'È': '7', u'!': '8', u'Ç': '9',
              u'À': '0', u'Q': 'A'}
        for i in code:
            out += dd[i]
        return out

    is_rfid_code = True
    code = code.upper()
    if code[0] in u'&É"\'(§È!ÇÀABCDEF':
        code = decode_caps_lock(code)
    try:
        int_code = int(code)
        if len(code) == 8:
            #code is already a hex code with decimals only
            pass
        else:
            if int_code < 100000:
                #student code
                is_rfid_code = False
            else:
                #a decimal number that needs to be converted
                h = '{:0>8}'.format(hex(int_code).split('x')[-1].upper())
                code = h[6:8] + h[4:6] + h[2:4] + h[0:2]
    except:
        #the code contains hex characters, hence is already correct
        pass
    return is_rfid_code, code

#show a list of registrations
@registration.route('/registration', methods=['GET', 'POST'])
@login_required
def register():

    try:
        if 'code' in request.form:
            is_rfid_code, code = decode_code(request.form['code'])
            print('{} {}'.format(is_rfid_code, code))

            if is_rfid_code:
                reg = Registration.query.filter(Registration.rfidcode2 == code).first()
                if not reg:
                    Registration.query.filter(Registration.rfidcode == code).first()
            else:
                reg = Registration.query.filter(Registration.studentcode == code).first()
            if reg:
                print(reg)
    except:
        pass


    series = Series.query.order_by(Series.sequence).all()
    #
    # try:
    #     if 'code' in request.form:
    #         code = request.form['code'].upper()
    #         if 'add_student' in request.form:
    #             if request.form['add_student']=='Bewaar': #s
    # ave new student
    #                 first_name = request.form['new_first_name']
    #                 last_name = request.form['new_last_name']
    #                 classgroup = request.form['new_classgroup']
    #                 if last_name == '' or first_name == '' or classgroup == '':
    #                     flash('Naam en/of klas is niet volledig, probeer opnieuw')
    #                     log.info('add student : bad name and/or classgroup')
    #                 else:
    #                     registration = Registration(first_name=first_name, last_name=last_name, student_code=code, classgroup=classgroup)
    #                     db.session.add(registration)
    #                     db.session.commit()
    #                     flash(u'Nieuwe student: {} {} {} met code {}'.format(first_name, last_name, classgroup, code))
    #                     log.info(u'added student : {} {} {} with code {}'.format(first_name, last_name, classgroup, code))
    #         else:
    #             registration_id = int(request.form['registration_id'])
    #             try:
    #                 test_code = int(code) #check if it is an integer, in which case, try to find  it in the database
    #                 registration = Registration.query.filter(Registration.studentcode == code).first()
    #                 if registration:
    #                     student_name = u'{} {}'.format(registration.first_name, registration.last_name)
    #                     student_code = u'{}'.format(code)
    #                     classgroup = registration.classgroup
    #                     registration_id = registration.id
    #                 else:
    #                     #new student, code should start at 20000
    #                     if test_code >= 20000:
    #                         new_student = True
    #                         registration_id = test_code
    #                         barcode = code  #show student code
    #                     else:
    #                         flash(u'Onbekende code.  Nieuwe leerlingcode start vanaf 20000')
    #                         log.info(u'unknown code.  New studentcode starts from 20000')
    #                         registration_id = -1
    #             except:
    #                 if code[:3] == 'URS':
    #                     #add a computer code.  Old computer code will be overwritten
    #                     registration = Registration.query.get(registration_id)
    #                     if registration:
    #                         registration.computer_code = None if code == u'URSDELETE' else code
    #                         registration.timestamp = datetime.datetime.now()
    #                         registration.user_id = current_user.id
    #                         db.session.commit()
    #                         log.info(u'assigned pc {} to student code {}'.format(code, registration.student_code))
    #                         registration_id = -1
    #                     else:
    #                         flash(u'Eerst leerlingcode ingeven')
    #                         log.info(u'First enter student code')
    #                         registration_id = -1
    #                 else:
    #                     flash(u'Onbekende code.  Code moet beginnen met een cijfer of URS')
    #                     log.info(u'unknown code (does not start with a cypher or URS)')
    #                     registration_id = -1
    #
    # except IntegrityError as e: #computer code already present
    #     db.session.rollback()
    #     r = Registration.query.filter(Registration.computer_code==code).first()
    #     flash(u'Deze computer code is reeds toegewezen aan {} {}'.format(r.last_name, r.first_name))
    #     log.warning(u'PC {} is already assigned to {}.  error {}'.format(code, r.student_code, e))
    #     registration_id = -1
    # except Exception as e:
    #     db.session.rollback()
    #     flash(u'Onbekende fout, probeer opnieuw')
    #     log.warning(u'unknow error : {}'.format(e))
    #     registration_id = -1

    registrations=[]

#    registrations = Registration.query.filter(Registration.computer_code<>'', Registration.user_id==current_user.id).order_by(Registration.timestamp.desc()).all()
    return render_template('registration/registration.html',
                           series = series,
                           registrations=registrations)

