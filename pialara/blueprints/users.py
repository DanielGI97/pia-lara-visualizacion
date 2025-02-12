from werkzeug.security import generate_password_hash

from datetime import datetime, timedelta
import json
from bson.objectid import ObjectId
from flask import Blueprint, render_template, request
from urllib import request

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)

from flask_login import login_required, current_user
from pialara.decorators import rol_required
from pialara.models.Usuario import Usuario
# Cambios grafica ---
# Importamos el modelo de Audios
from pialara.models.Audios import Audios
# ---
from pialara.models.Enfermedades import Enfermedades
from pialara.models.Disfonias import Disfonias
from pialara.decorators import rol_required

bp = Blueprint('users', __name__, url_prefix='/users')

@bp.route('/')
@login_required
@rol_required(['admin', 'tecnico', 'cliente'])
def index():
    u = Usuario()
    # Cambios grafica ---
    # Creamos un objeto audios para poder hacer un find sobre los mismos.
    a = Audios()
    # ---
    users = []
    audios = []
    logged_rol = current_user.rol
    url = 'users/index.html'

    # Obtener la fecha actual
    fecha_actual = datetime.now().date()

    # Restar 6 semanas a la fecha actual
    fecha_6_semanas_atras = fecha_actual - timedelta(weeks=6)

    from_dt = datetime.strptime('2023-01-01','%Y-%m-%d')
    to_dt = datetime.strptime('2024-01-01','%Y-%m-%d')


    #"$gte": fecha_6_semanas_atras,
    #"$lte": fecha_actual

    if logged_rol == "admin":
        users = u.find()
    elif logged_rol == "tecnico":
        users = u.find({"rol": {"$eq": 'cliente'}, "parent": {"$eq": current_user.email}})
        #AGREGACION PARA CONSULTAR TODOS LOS AUDIOS DE UN CLIENTE.

        audios = a.aggregate([{"$match": { "usuario.parent": current_user.email }},
                              { "$group": { "_id": "$usuario.mail", "cantidad_audios": { "$sum": 1 }
                               }
                              }
                            ])

        #AGREGACION PARA CONSULTA DE 6 SEMANAS ATRÁS
        # audios = a.aggregate([
        #                         {
        #                             "$match": {
        #                                 "fecha": {
        #                                     "$gte": from_dt,
        #                                     "$lte": to_dt
        #                                 }
        #                             }
        #                         },
        #                         {
        #                             "$group": {
        #                                 "_id": {
        #                                     "week": { "$week": "$fecha" },
        #                                     "usuario": "$usuario.mail"
        #                                 },
        #                                 "cantidad_audios": { "$sum": 1 }
        #                             }
        #                         },
        #                         {
        #                             "$group": {
        #                                 "_id": "$_id.usuario",
        #                                 "audios_por_semana": {
        #                                     "$push": {
        #                                         "semana": "$_id.week",
        #                                         "cantidad_audios": "$cantidad_audios"
        #                                     }
        #                                 }
        #                             }
        #                         },
        #                         {
        #                             "$sort": {
        #                                 "_id": 1
        #                             }
        #                         }
        #                     ])

        #COMO TRATAR LA INFORMACION DE LA CONSULTA DE 6 SEMANAS ATRAS
        # audios_data = []

        # grafica = {}
        
        # for audio in audios:
        #     audios_data.append(audio)

        # for audio in audios_data:
        #     id_usuario = audio['_id']
        #     cantidades = {}
        #     for semana in audio['audios_por_semana']:
                
        #         cantidades[semana['semana']]=semana['cantidad_audios']
                
        #     grafica[id_usuario]=cantidades
        
        # semanas_label = []
        # data_grafico = []
        # id_usuario_label = grafica

        # print("terminamos audios_data")
        audios_data = list(audios)
        usuarios = []
        cantidad = []
        for audio in audios_data:
            usuarios.append(str(audio['_id']))
            cantidad.append(int(audio['cantidad_audios']))
        usuarios_json = json.dumps(usuarios)
        cantidad_json = json.dumps(cantidad)        
    else:
        return redirect(url_for('audios.client_tag'))

    return render_template(url, users=users, usuarios=usuarios_json, cant=cantidad_json, user_name='')


@bp.route('/', methods=['POST'])
@login_required
@rol_required(['admin', 'tecnico'])
def search_user():
    user_name = request.form.get('userName')
    u = Usuario()

    logged_rol = current_user.rol

    url = 'users/index.html'
    if logged_rol == "admin":
        users = u.find({'nombre': {"$regex": user_name, '$options': 'i'}})
    else:
        users = u.find({"rol": {"$eq": 'cliente'}, 'nombre': {"$regex": user_name, '$options': 'i'}, "parent": {"$eq": current_user.email}})
  
    return render_template(url, users=users, user_name=user_name)

@bp.route('/create')
@login_required
@rol_required(['admin', 'tecnico'])
def create():
    u = Usuario()
    logged_rol = current_user.rol

    enfermedades = Enfermedades()
    disfonias = Disfonias()

    return render_template(
        'users/create.html',
        rol=logged_rol,
        enfermedades=enfermedades.find(),
        disfonias=disfonias.find()
    )

@bp.route('/create', methods=['POST'])
@login_required
def create_post():
    nombreAdmin = request.form.get('nombre_admin')
    emailAdmin = request.form.get('email_admin')
    pass1 = request.form.get('pass1')
    pass2 = request.form.get('pass2')

    nombreTecnico = request.form.get('nombre_tecnico')
    emailTecnico = request.form.get('email_tecnico')

    nombreCliente = request.form.get('nombre_cliente')
    emailCliente = request.form.get('email_cliente')
    fNacCliente = request.form.get('fnac_cliente')
    sexoCliente = request.form.get('sexo_cliente')
    provinciaCliente = request.form.get('provincia_cliente')
    enfermedadesCliente = request.form.getlist('enfermedades')
    disCliente = request.form.getlist('dis')

    user = Usuario()

    if pass1 != pass2:
        flash("Las contraseñas no son iguales", 'danger')
        return render_template('users/create.html')


    result = None

    if nombreAdmin and not existeCorreo(emailAdmin):

        newUser = {"nombre": nombreAdmin, "mail": emailAdmin, "rol": "admin",
                   "password": generate_password_hash(pass1, method='sha256'),
                   "fecha_nacimiento":datetime.now(), "ultima_conexion":datetime.now()}
        result = user.insert_one(newUser)

    elif nombreTecnico and not existeCorreo(emailTecnico):
        newUser = {"nombre": nombreTecnico, "mail": emailTecnico, "rol": "tecnico",
                   "password": generate_password_hash(pass1, method='sha256'),
                   "fecha_nacimiento": datetime.now(), "ultima_conexion": datetime.now()}
        result = user.insert_one(newUser)

    elif nombreCliente and not existeCorreo(emailCliente):
        fecha = datetime.strptime(fNacCliente, '%Y-%m-%d')
        newUser = {"nombre": nombreCliente, "mail": emailCliente, "rol": "cliente",
                   "password": generate_password_hash(pass1, method='sha256'),
                   "fecha_nacimiento": fecha, "ultima_conexion": datetime.now(),
                   "sexo": sexoCliente, "provincia": provinciaCliente,
                   "enfermedades": enfermedadesCliente, "dis": disCliente,
                   "parent": current_user.email, "cant_audios":0}
        result = user.insert_one(newUser)


    # Comprobar el resultado y mostrar mensaje
    if not result == None and result.acknowledged:
        flash('Usuario creado correctamente', 'success')
        return redirect(url_for('users.index'))
    else:
        flash('El usuario no se ha creado. Error genérico', 'danger')
        return redirect(url_for('users.create'))


def existeCorreo(email):
    user = Usuario()
    aux = user.count_documents({'mail': email})
    if aux > 0:
        return True

    return False

@bp.route('/update/<id>', methods=['GET'])
@login_required
def update(id):
    u = Usuario()
    model = u.find_one({'_id': ObjectId(id)})

    return render_template('users/update.html', model=model)


@bp.route('/update/<id>', methods=['POST'])
@login_required
def update_post(id):
    usu = Usuario()
    nombre = request.form.get('nombre')
    email = request.form.get('email')
    font_size = request.form.get('font_size')
    font_size_flota = float(font_size)

    if font_size_flota == session['font_size']:
        resultado = usu.update_one({'_id': ObjectId(id)}, {"$set": {'nombre': nombre, 'mail': email}})
    else:
        resultado = usu.update_one({'_id': ObjectId(id)}, {"$set": {'nombre': nombre, 'mail': email, 'font_size': font_size_flota}})

    if resultado.acknowledged & resultado.modified_count == 1:
        session['font_size'] = font_size_flota
        flash('Usuario actualizado correctamente', 'success')
        return redirect(url_for('users.index'))
    elif resultado.acknowledged & resultado.modified_count == 0:
        flash('Error al actualizar el usuario, inténtelo de nuevo...', 'danger')
        return redirect(url_for('users.update', id=id))
    else:
        flash('La usuario no se ha actualizado. Error genérico', 'danger')
        return redirect(url_for('users.index'))

@bp.route('/consent')
@login_required
def consent():
    logged_rol = current_user.rol
    login_url = url_for('users.index')

    # if logged_rol == 'cliente':
    #    login_url = url_for('audios.client_tag')

    return render_template('users/consent.html', login_url=login_url)
