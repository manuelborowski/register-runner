# -*- coding: utf-8 -*-
# app/settings/views.py

from flask import render_template, redirect, url_for, request, flash, send_file, abort, make_response
from flask_login import login_required
from ..base import get_global_setting_current_schoolyear, set_global_setting_current_schoolyear, get_setting_simulate_dayhour, set_setting_simulate_dayhour
from . import settings
from .. import db, app, log, ms2m_s_ms
from ..models import Settings, Registration, Series
from flask_login import current_user

from io import StringIO
import unicodecsv as csv
import  csv
import random

def check_admin():
    if not current_user.is_admin:
        abort(403)

def get_settings_and_show():
    return render_template('settings/settings.html',
                           schoolyear = get_global_setting_current_schoolyear(),
                           simulate_dayhour = get_setting_simulate_dayhour(),
                           title='settings')

@settings.route('/settings', methods=['GET', 'POST'])
@login_required
def show():
    return get_settings_and_show()

@settings.route('/settings/save', methods=['GET', 'POST'])
@login_required
def save():
    if request.form['button'] == 'Bewaar':
        if 'schoolyear' in request.form:
           set_global_setting_current_schoolyear(request.form['schoolyear'])
    if 'simulate_dayhour' in request.form:
        set_setting_simulate_dayhour(request.form['simulate_dayhour'])
    return get_settings_and_show()

@settings.route('/settings/purge_database', methods=['GET', 'POST'])
@login_required
def purge_database():
    try:
        Registration.query.delete()
        Series.query.delete()
        db.session.commit()
    except Exception as e:
        flash('Kan niet verwijderen...')
    return redirect(url_for('settings.show'))

@settings.route('/settings/purge_times', methods=['GET', 'POST'])
@login_required
def purge_times():
    try:
        Registration.query.update(dict(time_ran=None, time_registered=None))
        Series.query.update(dict(running=False, starttime=None))
        db.session.commit()
    except Exception as e:
        flash('Kan niet verwijderen...')
    return redirect(url_for('settings.show'))


@settings.route('/settings/random_times', methods=['GET', 'POST'])
@login_required
def random_times():
    try:
        rl = Registration.query.all()
        for r in rl:
            r.time_ran  = random.randint(300000, 1800000) #random time between 5 and 30 minutes
        db.session.commit()
    except Exception as e:
        flash('Kan geen willekeurige tijden toevoegen...')
    return redirect(url_for('settings.show'))



@settings.route('/settings/upload_file', methods=['GET', 'POST'])
@login_required
def upload_file():
    if request.files['upload_students']: import_students(request.files['upload_students'])
    return redirect(url_for('settings.show'))


#import excel file
#sheet "studenten"
#NAAM           last_name
#VOORNAAM       first_name
#GESLACHT       gender
#LEERLINGNUMMER studentcode
#KLAS           classgroup
#RFID           rfidcode
#REEKS          series (pointer to)
#sheet "reeksen"
#NAAM           name
#NUMMER         series-id (not stored)
#VOLGORDE       sequence


def import_students(rfile):
    try:
        log.info('Import students from : {}'.format(rfile))
        #rrf = pyexcel.book(file_name = rfile.filename)
        rrf = request.get_book(field_name='upload_students')

        #read and store the series information
        #first row contains the headers...
        try:
            rrf.reeksen.name_columns_by_row(0)
            series_dict = {}
            for i in range(rrf.reeksen.number_of_rows()):
                if rrf.reeksen[i, 'NAAM'] != '' and rrf.reeksen[i, 'VOLGORDE'] != '' and rrf.reeksen[i, 'NUMMER'] != '':
                    find_series = Series.query.filter(Series.name == rrf.reeksen[i, 'NAAM']).first()
                    if find_series:
                        series_dict[rrf.reeksen[i, 'NUMMER']] = find_series
                    else:
                        ns = Series(name=rrf.reeksen[i, 'NAAM'], sequence=rrf.reeksen[i, 'VOLGORDE'])
                        series_dict[rrf.reeksen[i, 'NUMMER']] = ns
                        db.session.add(ns)
            db.session.commit()
        except Exception as e:
            flash('Kan blad \'reeksen\' niet vinden')
            log.warning('cannot find sheet reeksen: {}'.format(e))

        #read and store the student information
        #first row contains the headers...
        try:
            rrf.studenten.name_columns_by_row(0)
            empty_rfid_ctr = 0
            find_student = Registration.query.filter(Registration.rfidcode.like('LEEG#%')).order_by(Registration.rfidcode.desc()).first()
            if find_student:
                empty_rfid_ctr = int(find_student.rfidcode.split('#')[-1]) + 1
            nbr_students = 0
            for i in range(rrf.studenten.number_of_rows()):
                if rrf.studenten[i, 'VOORNAAM'] != '' and rrf.studenten[i, 'NAAM'] != '' and \
                    rrf.studenten[i, 'KLAS'] != '' and rrf.studenten[i, 'LEERLINGNUMMER'] != '' and \
                    rrf.studenten[i, 'REEKS'] != '' and rrf.studenten[i, 'GESLACHT'] != '':
                    find_student = Registration.query.filter(Registration.studentcode == rrf.studenten[i, 'LEERLINGNUMMER']).first()
                    if not find_student:
                        if rrf.studenten[i, 'RFID'] == '':
                            rfidcode = 'LEEG#{}'.format(empty_rfid_ctr)
                            empty_rfid_ctr += 1
                        else:
                            rfidcode = rrf.studenten[i, 'RFID']
                        nr = Registration(first_name = rrf.studenten[i, 'VOORNAAM'], last_name=rrf.studenten[i, 'NAAM'], \
                                        gender = rrf.studenten[i, 'GESLACHT'],
                                        classgroup = rrf.studenten[i, 'KLAS'],
                                        studentcode = rrf.studenten[i, 'LEERLINGNUMMER'],
                                        rfidcode = rfidcode,
                                        series=series_dict[int(rrf.studenten[i, 'REEKS'])])
                        db.session.add(nr)
                        nbr_students += 1
                    else:
                        log.warning('student with code {} already present, skip'.format(rrf.studenten[i, 'LEERLINGNUMMER']))
                else:
                    log.warning('could not add student : {}'.format(i))
            db.session.commit()
            log.info('import: added {} students'.format(nbr_students))
            flash('{} leerlingen zijn geimporteerd'.format(nbr_students))
        except Exception as e:
            flash('Probleem met excel-blad \'studenten\'')
            log.warning('cannot find sheet studenten: {}'.format(e))

    except Exception as e:
        flash('Kan bestand niet importeren')
        log.warning('cannot import: {}'.format(e))

#export a list of assets
@settings.route('/settings/export', methods=['GET', 'POST'])
@login_required
def exportcsv():
    try:
        headers = [
            'NAAM',
            'VOORNAAM',
            'GESLACHT',
            'KLAS',
            'LEERLINGNUMMER',
            'TIJD',
            'TIJD(MS)',
            'SERIE'
        ]
        rows = []
        for r in Registration.query.join(Series).all():
            time_ran = ms2m_s_ms(r.time_ran)
            rows.append((
                    r.last_name,
                    r.first_name,
                    r.gender,
                    r.classgroup,
                    r.studentcode,
                    time_ran,
                    r.time_ran,
                    r.series.name))

        si = StringIO()
        cw = csv.writer(si, delimiter=';')
        cw.writerow(headers)
        cw.writerows(rows)
        output = make_response(si.getvalue())
        output.headers["Content-Disposition"] = "attachment; filename=registraties.csv"
        output.headers["Content-type"] = "text/csv"
        return output
    except Exception as e:
        log.error('Could not export file {}'.format(e))
        return redirect(url_for('settings.show'))
