from flask_appbuilder import Model
from flask_appbuilder.models.mixins import AuditMixin
from flask_login import UserMixin
from flask_appbuilder.models.decorators import renders
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Time, func, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
# from flask_bcrypt import bcrypt

from .. import db
from datetime import datetime
import calendar



class Card(Model, AuditMixin):
    __public__ = ['id', 'card_number', 'time']
    __tablename__ = 'carddata'

    id = Column(Integer, primary_key=True)
    card_number = Column(String(32), index=True, nullable=False, doc="Card access number")
    time = Column(DateTime, nullable=False)
    access = Column(String(20), doc="Access")
    card_reader_id = Column(Integer, ForeignKey('timecard.id'))
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship('User', cascade='all, delete', backref='pristupy')

    @renders('time')
    def render_time(self):
        return self.time.strftime('%Y-%m-%d %H:%M:%S') if self.time else ''
    
    @staticmethod
    def find_by_number(card_number):
        return db.session.query(Card).filter_by(card_number=card_number).first()

    @classmethod
    def stravenky(cls, month, card_number):
        narok = 0
        form = (
            db.session.query(
                func.strftime('%Y-%m-%d', cls.time).label("date"),
                func.max(func.strftime('%H:%M', cls.time)).label("Max"),
                func.min(func.strftime('%H:%M', cls.time)).label("Min"),
                (func.max(cls.time) - func.min(cls.time)).label("Rozdil")
            )
            .filter(func.strftime('%Y-%m', cls.time) == month)
            .filter(cls.card_number == card_number)
            .group_by(func.strftime('%Y-%m-%d', cls.time))
            .all()
        )
        for n in form:
            if n.rozdil >= 3:
                narok += 1
        return narok

    @staticmethod
    def get_all_by_user_id(user_id):
        return (
            db.session.query(Card.time, Card.card_reader_id, Card.access)
            .filter_by(id_user=user_id)
            .all()
        )

class Group(Model, AuditMixin):
    __tablename__ = 'groups'

    id = Column(Integer, primary_key=True)
    monday = Column(Integer, default=False)
    tuesday = Column(Integer, default=False)
    wednesday = Column(Integer, default=False)
    thursday = Column(Integer, default=False)
    friday = Column(Integer, default=False)
    saturday = Column(Integer, default=False)
    sunday = Column(Integer, default=False)
    group_name = Column(String(40), nullable=False, index=True)
    access_time_from = Column(Time, nullable=True, index=True)
    access_time_to = Column(Time, nullable=True, index=True)
    timecard = relationship('Group_has_timecard', backref='group')

    @renders('access_time_from')
    def render_access_time_from(self, value):
        return value.strftime('%H:%M') if value else ''

    @renders('access_time_to')
    def render_access_time_to(self, value):
        return value.strftime('%H:%M') if value else ''
    
    @staticmethod
    def get_group_list():
        return db.session.query(Group.id, Group.group_name, Group.access_time_from, Group.access_time_to).all()

    @staticmethod
    def find_access_time(group_id):
        return db.session.query(Group).filter_by(id=group_id).all()

    @staticmethod
    def get_group_name(group_id):
        return db.session.query(Group.group_name).filter_by(id=group_id).scalar()

    @staticmethod
    def get_id_name():
        return db.session.query(Group.id, Group.group_name).all()

    @staticmethod
    def get_time_from(group_id):
        return db.session.query(Group.access_time_from).filter_by(id=group_id).scalar()

    @staticmethod
    def get_time_to(group_id):
        return db.session.query(Group.access_time_to).filter_by(id=group_id).scalar()


class Group_has_timecard(Model):
    __tablename__ = 'group_has_timecard'

    group_id = Column(Integer, ForeignKey('groups.id'), primary_key=True)
    timecard_id = Column(Integer, ForeignKey('timecard.id'), primary_key=True)
    timecard = relationship("Timecard", backref="group_has_timecard")

    @renders('timecard')
    def render_timecard(self, value):
        return f"{value}" if value else ''
    
    @staticmethod
    def find_timecard(group_id):
        return db.session.query(Group_has_timecard.timecard_id).filter_by(group_id=group_id).all()

    @staticmethod
    def find_to_delete(timecard_id, group_id):
        return (
            db.session.query(Group_has_timecard.group_id)
            .filter(Group_has_timecard.group_id == group_id, Group_has_timecard.timecard_id == timecard_id)
            .delete()
        )

    @staticmethod
    def timecard_in_group():
        return (
            db.session.query(Group_has_timecard.id, Group_has_timecard.group_id, Timecard.id, Timecard.timecard_name)
            .join(Group_has_timecard.timecard)
            .all()
        )


class Log(Model):
    __tablename__ = 'log'
    __public__ = ['time', 'text']

    id = Column(Integer, primary_key=True, autoincrement=True)
    time = Column(DateTime)
    text = Column(String(80))

    @renders('time')
    def render_time(self, value):
        return value.strftime('%d-%m-%Y %H:%M:%S') if value else ''

    def __repr__(self):
        return f"<Log(id={self.id}, time={self.time}, text='{self.text}')>"


class Timecard(Model, AuditMixin):
    __tablename__ = 'timecard'

    id = Column(Integer, primary_key=True)
    timecard_name = Column(String(30), nullable=False, index=True)
    timecard_head = Column(String(30), nullable=False, index=True)
    entreader_id = Column(String(60), index=True)
    pushopen = Column(String(60))
    card_data = relationship('Card', backref='timecard')

    @staticmethod
    def get_timecard_list():
        return db.session.query(Timecard.id, Timecard.timecard_name, Timecard.timecard_head).all()

    @staticmethod
    def get_name(id):
        return db.session.query(Timecard.timecard_name).filter_by(id=id).first()

    @staticmethod
    def get_id_and_name():
        return db.session.query(Timecard.id, Timecard.timecard_head).all()

    @staticmethod
    def get_id_name():
        return db.session.query(Timecard.id, Timecard.timecard_name).all()
    

class User(Model, UserMixin, AuditMixin):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    activate_token = Column(String(128), nullable=True, doc="Activation token for email verification")
    email = Column(String(64), nullable=True, unique=True, index=True, doc="The user's email address.")
    password_hash = Column(String(128))
    username = Column(String(64), nullable=True, unique=True, index=True, doc="The user's username.")
    verified = Column(Boolean(name="verified"), nullable=False, default=False)
    card_number = Column(String(32), unique=False, index=True, doc="Card access number")
    name = Column(String(60), unique=False, index=True, doc="Name")
    second_name = Column(String(60), unique=False, index=True, doc="Second name")
    access = Column(String(1), index=True, doc="Access")
    chip_number = Column(String(10), unique=False, index=True, doc="Chip number", nullable=False)
    mazej = Column(Boolean(name="mazej"), unique=False, doc="pro mazani")

    @hybrid_property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    # @password.setter
    # def password(self, password):
    #    self.password_hash = bcrypt.generate_password_hash(password, app_config.BCRYPT_LOG_ROUNDS)

    # def verify_password(self, password):
    #     return bcrypt.check_password_hash(self.password_hash, password)

    def is_verified(self):
        return self.verified is True

    @staticmethod
    def find_by_email(email):
        return db.session.query(User).filter_by(email=email).scalar()

    @staticmethod
    def find_by_username(username):
        return db.session.query(User).filter_by(username=username).scalar()

    @staticmethod
    def find_by_number(card_number):
        return db.session.query(User).filter_by(card_number=card_number).scalar()

    @staticmethod
    def get_id(card_number):
        return db.session.query(User.id).filter_by(card_number=card_number).scalar()

    @staticmethod
    def get_id_and_access(card_number):
        return db.session.query(User.id, User.access).filter_by(card_number=card_number).first()

    @staticmethod
    def access_by_group(chip, fromcte):
        acctualtime = datetime.now()
        dayofweek = acctualtime.weekday()
        timenow = acctualtime.time()

        chip = str(chip).zfill(10)
        user_groups = db.session.query(Group) \
            .filter(getattr(Group, calendar.day_name[dayofweek]) == True) \
            .filter(Group.access_time_from <= timenow) \
            .filter(Group.access_time_to >= timenow) \
            .join(User_has_group).join(User).filter(User.chip_number.like(chip)).join(Group_has_timecard) \
            .join(Timecard).filter(Timecard.identreader == fromcte).all()

        return len(user_groups) > 0

    @staticmethod
    def find_by_chip(chip_number):
        test_chip = str(chip_number).zfill(10)
        return db.session.query(User).filter(User.chip_number.like(test_chip)).first()

    @staticmethod
    def all_users():
        return db.session.query(User.id, User.name, User.second_name).all()

    @staticmethod
    def all_names():
        return db.session.query(User.name).all()

    @staticmethod
    def in_group():
        return db.session.query(User.id, User.name, User.second_name)

    @staticmethod
    def find_user_by_id(id):
        return db.session.query(User).filter_by(id=id).all()

    @staticmethod
    def user_in_group():
        return db.session.query(User.id, User.name, User.second_name, User_has_group.group_id, Group.group_name) \
            .join(User_has_group).join(Group).all()

    @staticmethod
    def one_user_by_id(id):
        return db.session.query(User.name, User.second_name).filter_by(id=id).first()

    @staticmethod
    def get_name(id):
        return db.session.query(User.name).filter_by(id=id).first()

    @staticmethod
    def users_in_specific_group(group_id):
        return db.session.query(User.id, User.name, User.second_name, User_has_group.group_id) \
            .join(User_has_group).filter_by(group_id=group_id).all()
    

class User_has_group(Model):
    __tablename__ = 'user_has_group'

    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    group_id = Column(Integer, ForeignKey('groups.id'), primary_key=True)
    group = relationship("Group", back_populates="user_has_group")

    @staticmethod
    def find_timecard_by_userid(id):
        group_id = db.session.query(User_has_group.group_id).filter_by(user_id=id).all()
        return Group.find_access_time(group_id)

    @staticmethod
    def get_all():
        return db.session.query(User_has_group.user_id, User_has_group.group_id).all()

    @staticmethod
    def users_in_group(group_id):
        return db.session.query(User_has_group.user_id).filter_by(group_id=group_id).all()

    @staticmethod
    def get_group_name():
        return db.session.query(User_has_group.group_id, Group.group_name).all()

    @staticmethod
    def compare_users(id):
        return db.session.query(User_has_group.group_id).filter_by(user_id=id).all()

    @staticmethod
    def find_to_delete(user, group):
        return db.session.query(User_has_group).filter(User_has_group.user_id == user, User_has_group.group_id == group).delete()

    @staticmethod
    def find_id(user_id, group_id):
        return db.session.query(User_has_group.id).filter(User_has_group.user_id == user_id, User_has_group.group_id == group_id).scalar()