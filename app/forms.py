# -*- coding: utf-8 -*-
#app/forms.py

from flask_wtf import FlaskForm
from wtforms import SelectField
from models import Classgroup, Teacher


class ClassgroupFilter(FlaskForm):
    def __init__(self, *args, **kwargs):
        super(ClassgroupFilter, self).__init__(*args, **kwargs)
        self.classgroup.choices=Classgroup.get_choices_with_empty_list()

    classgroup = SelectField('')

class TeacherFilter(FlaskForm):
    def __init__(self, *args, **kwargs):
        super(TeacherFilter, self).__init__(*args, **kwargs)
        self.teacher.choices=Teacher.get_choices_with_empty_list()

    teacher = SelectField('')


# class StatusFilter(FlaskForm):
#     def __init__(self, *args, **kwargs):
#         super(StatusFilter, self).__init__(*args, **kwargs)
#         self.status.choices=zip(Asset.Status.get_list_with_empty(), Asset.Status.get_list_with_empty())
#
#     status = SelectField('')
#
# class SupplierFilter(FlaskForm):
#     def __init__(self, *args, **kwargs):
#         super(SupplierFilter, self).__init__(*args, **kwargs)
#         sl = Supplier.query.order_by(Supplier.name).all()
#         sl.insert(0, '')
#         self.supplier.choices=zip(sl, sl)
#
#     supplier = SelectField('')
#
# class DeviceFilter(FlaskForm):
#     def __init__(self, *args, **kwargs):
#         super(DeviceFilter, self).__init__(*args, **kwargs)
#         dl = Device.query.order_by(Device.brand).all()
#         dl.insert(0, '')
#         self.device.choices=zip(dl, dl)
#
#     device = SelectField('')

class NonValidatingSelectFields(SelectField):
    def pre_validate(self, form):
        pass