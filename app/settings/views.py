# -*- coding: utf-8 -*-
# app/settings/views.py

from flask import render_template, redirect, url_for, request, flash, send_file, abort
from flask_login import login_required
from ..base import get_global_setting_current_schoolyear, set_global_setting_current_schoolyear, get_setting_simulate_dayhour, set_setting_simulate_dayhour
from . import settings
from .. import db, app, log
from ..models import Settings, Registration
from flask_login import current_user

import unicodecsv as csv
import cStringIO, csv

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
        if 'delete_list' in request.form:
            pass
            # for d in document_type_list:
            #     if d in request.form['delete_doc']:
            #         if get_doc_select(d) in request.form:
            #             for i in request.form.getlist(get_doc_select(d)):
            #                 os.remove(os.path.join(get_doc_path(d), i))
    except Exception as e:
        flash('Kan niet verwijderen...')
    return redirect(url_for('admin.show'))


@settings.route('/settings/upload_file', methods=['GET', 'POST'])
@login_required
def upload_file():
    if request.files['upload_students']: import_students(request.files['upload_students'])
    return redirect(url_for('settings.show'))

#NAAM           last_name
#VOORNAAM       first_name
#LEERLINGNUMMER student_code
#FOTO           photo
#KLAS           classgroup

def import_students(rfile):
    try:
        # format csv file :
        log.info('Import students from : {}'.format(rfile))
        students_file = csv.DictReader(rfile,  delimiter=';')
        #students_file = csv.DictReader(rfile,  delimiter=';', encoding='utf-8-sig')

        nbr_students = 0
        for s in students_file:
            #skip empy records
            if s['LEERLINGNUMMER'] != '' and s['VOORNAAM'] != '' and s['NAAM'] != '' and s['KLAS'] != '':
                #add student, if not already present
                find_student=Registration.query.filter(Registration.first_name == s['VOORNAAM'], Registration.last_name == s['NAAM'],
                                                       Registration.studentcode == s['LEERLINGNUMMER'], Registration.classgroup == s['KLAS']).first()
                if not find_student:
                    student = Registration(first_name=s['VOORNAAM'], last_name=s['NAAM'], student_code=s['LEERLINGNUMMER'], classgroup=s['KLAS'])
                    db.session.add(student)
                    nbr_students += 1

        db.session.commit()
        log.info('import: added {} students'.format(nbr_students))
        flash('Leerlingen zijn geimporteerd')

    except Exception as e:
        flash('Kan bestand niet importeren')
        log.warning('cannot import students')
    return redirect(url_for('settings.show'))

#export a list of assets
@settings.route('/settings/export', methods=['GET', 'POST'])
@login_required
def exportcsv():
    #The following line is required only to build the filter-fields on the page.
    csv_file = cStringIO.StringIO()
    headers = [
        'NAAM',
        'VOORNAAM',
        'KLAS',
        'LEERLINGNUMMER',
        'COMPUTER',
        'TIJD',
    ]

    rows = []
    for r in Registration.query.all():
        rows.append(
            {
                'NAAM': r.last_name,
                'VOORNAAM': r.first_name,
                'KLAS' : r.classgroup,
                'LEERLINGNUMMER': r.student_code,
                'COMPUTER': r.computer_code,
                'TIJD': r.timestamp,
            }
        )

    writer = csv.DictWriter(csv_file, headers, delimiter=';')
    writer.writeheader()
    for r in rows:
        writer.writerow(dict((k, v.encode('utf-8') if type(v) is unicode else v) for k, v in r.iteritems()))
    csv_file.seek(0)
    log.info('exported students')
    return send_file(csv_file, attachment_filename='registraties.csv', as_attachment=True)
