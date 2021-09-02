import time
import tkinter as tk
from datetime import datetime
from tkinter import messagebox
from tkinter.font import BOLD, Font
from tkinter.ttk import Label, Scale, Button
import webbrowser
import cv2
import sqlite3
import face_recognition
import numpy as np
from PIL import Image, ImageTk
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import img_to_array


class Application(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        # Configuração de detecção facial
        self.width, self.height = 800, 600
        self.countFacesFrame = 0
        self.MEDIA_PROB = 50.00
        self.encoding_list = list()
        self.fonte_pequena, self.fonte_media = 0.4, 0.7
        self.fonte = cv2.FONT_HERSHEY_SIMPLEX
        self.to_list = [['faces', 'categoria', 'probabilidade', 'data', 'hora']]
        self.category = ['young_male', 'adult_male', 'old_male', 'young_female', 'adult_female', 'old_female']
        self.category_count = {
            'young_male': 0,
            'adult_male': 0,
            'old_male': 0,
            'young_female': 0,
            'adult_female': 0,
            'old_female': 0
        }
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.padding = 10
        self.iniciar_processo = False
        # Banco de dados
        self.connection = sqlite3.connect('Main_DB.db')
        self.cursor_db = self.connection.cursor()
        # Widgets - Instanciar
        self.font_title = Font(self.master, weight=BOLD)
        self.master = master
        self.menubar = tk.Menu(self.master)
        self.webcam = Label(self.master, borderwidth=1, relief="sunken")
        self.webcam.grid(row=0, column=0, padx=self.padding, pady=self.padding)
        self.genero_root = Label(self.master)
        self.genero_root.grid(row=3, column=0, padx=self.padding, pady=self.padding)
        # Homem label
        self.string_homem_jovem = tk.StringVar(value="Jovem: 0")
        self.string_homem_adulto = tk.StringVar(value="Adulto: 0")
        self.string_homem_velho = tk.StringVar(value="Velho: 0")
        # Mulher label
        self.string_mulher_jovem = tk.StringVar(value="Jovem: 0")
        self.string_mulher_adulto = tk.StringVar(value="Adulto: 0")
        self.string_mulher_velho = tk.StringVar(value="Velho: 0")
        # Scale acurácia
        self.acuracia_titulo_string = tk.StringVar(value=f'Acurácia da detecção: {self.MEDIA_PROB}')
        # Button iniciar detecção facial
        self.start_detection_string = tk.StringVar(value="▶ INICIAR")
        # Inicializar Widgets
        self.create_table()
        self.create_widgets()

    def create_table(self):
        self.cursor_db.execute('CREATE TABLE IF NOT EXISTS genero_idade (young_male number, adult_male number,'
                               ' old_male number, young_female number, adult_female number, old_female number,'
                               'datetime TEXT)')

    # def insert(self):
    #     self.cursor_db.execute(f'INSERT INTO genero_idade VALUES ('2006-01-05','BUY','RHAT',100,35.14)')

    def create_widgets(self):
        self.create_widget_genero("Homem", 0, self.string_homem_jovem, self.string_homem_adulto,
                                  self.string_homem_velho)
        self.create_widget_genero("Mulher", 1, self.string_mulher_jovem, self.string_mulher_adulto,
                                  self.string_mulher_velho)
        self.create_widget_scale()
        self.create_widget_button(self.start_stop)
        self.show_frame()

    def create_widget_button(self, function):
        button = Button(self.master, textvariable=self.start_detection_string, command=function)
        button.grid(row=1, column=0, padx=self.padding, pady=self.padding)

    def create_widget_scale(self):
        label_acuracia = Label(self.master, borderwidth=1, relief="groove")
        acuracia_titulo = Label(label_acuracia, textvariable=self.acuracia_titulo_string, font=self.font_title)
        acuracia_start = Label(label_acuracia, text="0.0")
        acuracia_end = Label(label_acuracia, text="100.0")
        widget_acuracia = Scale(label_acuracia, value=self.MEDIA_PROB, from_=0, to=100, orient=tk.HORIZONTAL,
                                command=self.add_acuracia, length=100)
        widget_acuracia.set(self.MEDIA_PROB)
        acuracia_titulo.grid(row=0, column=0, columnspan=3, padx=self.padding, pady=self.padding)
        acuracia_start.grid(row=1, column=0, padx=self.padding, pady=self.padding)
        acuracia_end.grid(row=1, column=2, padx=self.padding, pady=self.padding)
        widget_acuracia.grid(row=2, column=0, columnspan=3, padx=self.padding, pady=self.padding)
        label_acuracia.grid(row=2, column=0, padx=self.padding, pady=self.padding)

    def create_widget_genero(self, text, column, string_jovem, string_adulto, string_velho):
        # Instanciamento
        label_main = Label(self.genero_root, borderwidth=1, relief="groove")
        genero_titulo = Label(label_main, text=text, font=self.font_title)
        label_jovem = Label(label_main, textvariable=string_jovem)
        label_adulto = Label(label_main, textvariable=string_adulto)
        label_velho = Label(label_main, textvariable=string_velho)
        # Posicionamento
        label_main.grid(row=0, column=column, padx=self.padding, pady=self.padding)
        genero_titulo.grid(row=0, column=1, padx=self.padding, pady=self.padding)
        label_jovem.grid(row=1, column=0, padx=self.padding, pady=self.padding)
        label_adulto.grid(row=1, column=1, padx=self.padding, pady=self.padding)
        label_velho.grid(row=1, column=2, padx=self.padding, pady=self.padding)

    def start_stop(self):
        titulo = "▶ INICIAR" if self.iniciar_processo else "■ PARAR"
        self.start_detection_string.set(titulo)
        self.iniciar_processo = not self.iniciar_processo

    def add_acuracia(self, value=0.0):
        self.MEDIA_PROB = float(value)
        self.acuracia_titulo_string.set(f'Acurácia da detecção: {round(float(value), 2)} %')

    def show_frame(self):
        conectado, frame = self.cap.read()
        if not conectado:
            messagebox.showerror("Atenção", "Webcam não está conectado!")
        else:
            frame = cv2.flip(frame, 1)
            if self.iniciar_processo:
                frame = self.face_detection(frame)
            cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
            img = Image.fromarray(cv2image)
            imgtk = ImageTk.PhotoImage(image=img)
            self.webcam.imgtk = imgtk
            self.webcam.configure(image=imgtk)
            # Loop for function
            self.webcam.after(10, self.show_frame)

    def face_detection(self, frame):
        t = time.time()
        arquivo_modelo = 'processing/model_01_human_category.h5'
        model = load_model(arquivo_modelo)
        face_cascade = cv2.CascadeClassifier('material/haarcascade_frontalface_default.xml')
        cinza = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(cinza, scaleFactor=1.2, minNeighbors=5, minSize=(30, 30))

        if len(faces) > 0:
            # hour = datetime.now().strftime("%H:%M:%S")
            # date = datetime.now().strftime("%d/%m/%Y")
            countFacesFlag = False
            facesError = False

            if self.countFacesFrame != len(faces):
                countFacesFlag = True

            for (x, y, w, h) in faces:
                frame_copy = frame.copy()
                final_frame = cv2.rectangle(frame, (x, y), (x + w, y + h + 10), (255, 50, 50), 2)
                roi = cinza[y:y + h, x:x + w]
                roi = cv2.resize(roi, (48, 48))
                roi = roi.astype("float") / 255.0
                roi = img_to_array(roi)
                roi = np.expand_dims(roi, axis=0)
                result = model.predict(roi)[0]
                if result is not None:
                    resultado = np.argmax(result)
                    prob = round(result[resultado] * 100, 2)
                    text = "{}: {:.2f}%".format(self.category[resultado], prob)
                    if countFacesFlag:
                        face_rgb = frame_copy[y:y + h, x:x + w, ::-1]
                        try:
                            current_encoding = face_recognition.face_encodings(face_rgb)[0]
                        except IndexError:
                            facesError = True
                        if self.encoding_list:
                            if not facesError:
                                compare = False
                                for old_encoding in self.encoding_list:
                                    compare_enconding = \
                                        face_recognition.compare_faces([current_encoding], old_encoding)[0]
                                    if compare_enconding:
                                        compare = True
                                if not compare:
                                    if prob >= self.MEDIA_PROB:
                                        print('Cadastrou um novo rosto: ', self.category[resultado])
                                        aux = [len(faces), self.category[resultado], prob, date, hour]
                                        self.to_list.append(aux)
                                        self.category_count[self.category[resultado]] = self.category_count[
                                                                                            self.category[
                                                                                                resultado]] + 1
                                        self.encoding_list.append(current_encoding)
                                    else:
                                        print(
                                            f'Não cadastrado, mas a probabilidade é {prob} de ser um {self.category[resultado]}')
                                        facesError = True
                        elif prob >= self.MEDIA_PROB and not facesError:
                            print('Cadastrou um novo rosto: ', self.category[resultado])
                            aux = [len(faces), self.category[resultado], prob, date, hour]
                            self.to_list.append(aux)
                            self.category_count[self.category[resultado]] = self.category_count[
                                                                                self.category[resultado]] + 1
                            self.encoding_list.append(current_encoding)
                        else:
                            facesError = True
                    self.countFacesFrame = 0
                    if not facesError:
                        self.countFacesFrame = len(faces)
                    cv2.putText(final_frame, text, (x, y - 10), self.fonte, self.fonte_media, (255, 255, 255), 1,
                                cv2.LINE_AA)
        else:
            self.countFacesFrame = len(faces)

        text_frame_04 = "{} faces now".format(len(faces))
        text_frame_03 = "Total detect {} people".format(len(self.to_list) - 1)
        text_frame_02 = "young_male: {} " \
                        "adult_male: {} " \
                        "old_male: {} " \
                        "young_female: {} " \
                        "adult_female: {} " \
                        "old_female: {}".format(
            self.category_count['young_male'],
            self.category_count['adult_male'],
            self.category_count['old_male'],
            self.category_count['young_female'],
            self.category_count['adult_female'],
            self.category_count['old_female']
        )
        text_frame_01 = "Frame processado em {:.2f} segundos".format(time.time() - t)

        cv2.putText(frame, text_frame_01, (20, self.height - 20), self.fonte, self.fonte_pequena, (250, 250, 250),
                    0,
                    lineType=cv2.LINE_AA)
        cv2.putText(frame, text_frame_02, (20, self.height - 35), self.fonte, self.fonte_pequena, (250, 250, 250),
                    0,
                    lineType=cv2.LINE_AA)
        cv2.putText(frame, text_frame_03, (20, self.height - 50), self.fonte, self.fonte_pequena, (250, 250, 250),
                    0,
                    lineType=cv2.LINE_AA)
        cv2.putText(frame, text_frame_04, (20, self.height - 65), self.fonte, self.fonte_pequena, (250, 250, 250),
                    0,
                    lineType=cv2.LINE_AA)
        return frame


def sobre():
    window = tk.Tk()
    window.title("Sobre")
    window.iconbitmap(default='icon/faceicon.ico')
    descricao = "Essa aplicação utiliza I.A para detecção facial e mapeamento por genêro e idade de cada rosto detectado, \n" \
                  "o mesmo utiliza de biometria facial para não repetir a contagem dos rostos."
    descricao_autor = "Desenvovido por Marcos Vinithius"
    url_linkedin = "https://www.linkedin.com/in/vinithius/"
    url_github = "https://github.com/vinithius2"

    text_descricao = Label(window, text=descricao)
    text_descricao_autor = Label(window, text=descricao_autor)

    label_contatos = Label(window, borderwidth=1, relief="raised")
    btn_linkedin = Button(label_contatos, text="Linkedin", command=lambda aurl=url_linkedin: webbrowser.open_new(aurl))
    btn_github = Button(label_contatos, text="Github", command=lambda aurl=url_github: webbrowser.open_new(aurl))
    label_email = Label(label_contatos, text="marcos.vinithius@gmail.com")

    text_descricao.grid(row=0, column=0, padx=10, pady=10)
    text_descricao_autor.grid(row=1, column=0, padx=10, pady=10)
    label_contatos.grid(row=3, column=0, padx=10, pady=10)
    btn_linkedin.grid(row=2, column=0, padx=10, pady=10)
    btn_github.grid(row=2, column=1, padx=10, pady=10)
    label_email.grid(row=2, column=2, padx=10, pady=10)
    app.mainloop()


root = tk.Tk()
root.title("Detector facial")
root.iconbitmap(default='icon/faceicon.ico')
menubar = tk.Menu(root)
filemenu = tk.Menu(menubar)
filemenu.add_command(label="Sobre", command=sobre)
menubar.add_cascade(label="File", menu=filemenu)
root.config(menu=menubar)

app = Application(master=root)
app.mainloop()
