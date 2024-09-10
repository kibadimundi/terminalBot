import datetime
import locale
import logging
import os
import subprocess
from functools import wraps

import telegram
import yaml
from telegram import Update
from telegram.ext import (CommandHandler, Application, ContextTypes)

global configuracion
configuracion = None


def cargar_configuracion_lectura(directorio=None):
    global configuracion
    locale.setlocale(locale.LC_ALL, 'es_ES.UTF-8')
    try:
        if (directorio != None):
            with open(directorio, 'r') as configuration:
                configuracion = yaml.safe_load(configuration)

    except Exception as e:
        logging.error("Error durante la carga de configuracion: " + str(e))
    return configuracion


def restricted(func):
    @wraps(func)
    def wrapped(update, context, *args, **kwargs):
        user_id = update.effective_user.id
        if not (user_id in configuracion['users']):
            print(f"Acceso no autorizado para el usuario {user_id}.")
            logging.warning("Acceso no autorizado para el usuario {}.".format(user_id))
            context.bot.send_message(chat_id=update.message.chat_id,
                                     text="No está autorizado a utilizar este bot")
            return
        return func(update, context, *args, **kwargs)

    return wrapped


def crear_log(configuracion):
    if not os.path.exists('log'):
        os.makedirs('log')
        logging.info("Directorio log creado")
    # Comprobamos si está el nivel
    if 'level' in configuracion['log']:
        nivel_log_num = getattr(logging, configuracion['log']['level'].upper())
        if not isinstance(nivel_log_num, int):
            raise ValueError('Nivel de log invalido: %s' % configuracion['log']['level'])
        logging.basicConfig(
            filename='log/BotSAO-' + str(datetime.datetime.today().strftime('%d.%m.%Y')) + '.log',
            filemode='a', encoding='utf-8', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            level=nivel_log_num)
        # logname="log/BotSAO-"
        # handler = TimedRotatingFileHandler(logname, when="midnight", interval=1)
        # handler.suffix = '%d_%m_%Y'
        # logging.addHandler(handler)
    else:
        logging.basicConfig(filename='log/BotSAO-' + str(datetime.datetime.today().strftime('%d.%m.%Y')) + '.log',
                            filemode='a', encoding='utf-8',
                            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                            level=logging.WARNING)


@restricted
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    kb = [
        [
            telegram.KeyboardButton('/verestado'),
            telegram.KeyboardButton('/reiniciar'),
            telegram.KeyboardButton('/apagar'),
            telegram.KeyboardButton('/log')
        ]
    ]
    await context.bot.send_message(chat_id=update.message.chat_id,
                             text="Bienvenido al bot para reiniciar SAO y ver su estado",
                             reply_markup=telegram.ReplyKeyboardMarkup(kb, resize_keyboard=True))


@restricted
async def ver_estado(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global configuracion
    result = subprocess.run(['/usr/bin/systemctl', 'status', 'tsuserverCC'], stdout=subprocess.PIPE)
    logging.info("El usuario con id" + str(update.message.chat_id) + "ha visto el estado del servicio")
    await context.bot.send_message(chat_id=update.message.chat_id,
                             text=result.stdout.decode('utf-8'))


@restricted
async def reiniciar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global configuracion

    result = subprocess.run(['/usr/bin/systemctl', 'restart', 'tsuserverCC'], stdout=subprocess.PIPE)
    logging.info("El usuario con id " + str(update.message.chat_id) + " ha reiniciado el servidor de SAO")

    await context.bot.send_message(chat_id=update.message.chat_id,
                             text="Servidor reiniciado con éxito. Resultado:" + result.stdout.decode('utf-8'))


async def apagar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global configuracion

    result = subprocess.run(['/usr/bin/systemctl', 'stop', 'tsuserverCC'], stdout=subprocess.PIPE)
    logging.info("El usuario con id " + str(update.message.chat_id) + " ha apagado el servidor de SAO")

    await context.bot.send_message(chat_id=update.message.chat_id,
                             text="Servidor apagado con éxito. Resultado:" + result.stdout.decode('utf-8'))


async def log(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global configuracion

    minilog = open('/home/servidorsao/tsuserverCC/logs/minilog.log', 'w')
    result = subprocess.Popen(['/usr/bin/tail', '-n', '200', '/home/servidorsao/tsuserverCC/logs/server.log'],
                              stdout=minilog)
    logging.debug(result.wait())
    minilog.close()
    fichero = open('/home/servidorsao/tsuserverCC/logs/minilog.log', 'rb')
    logging.info("El usuario con id " + str(update.message.chat_id) + " ha revisado el log del servidor de SAO")
    await context.bot.send_message(chat_id=update.message.chat_id,
                             text="Enviando el log con las últimas 200 lineas")
    await context.bot.sendDocument(chat_id=update.message.chat_id,
                             document=fichero, filename="Log.txt")
    fichero.close()


if __name__ == '__main__':
    directorio = "config.yaml"
    configuracion = cargar_configuracion_lectura(directorio=directorio)
    crear_log(configuracion)
    tokenbot = configuracion['telegram']['token_bot']
    application=Application.builder().token(tokenbot).build()

    application.add_handler( CommandHandler('start', start))
    application.add_handler(CommandHandler('verestado', ver_estado))
    application.add_handler(CommandHandler('reiniciar', reiniciar))
    application.add_handler(CommandHandler('apagar', apagar))
    application.add_handler(CommandHandler('log', log))
    application.run_polling(allowed_updates=Update.ALL_TYPES)

