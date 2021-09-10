import csv
import locale
import os
import sqlite3
import sys
import tkinter as tk
import webbrowser
from datetime import datetime
from tkinter import messagebox, filedialog, OptionMenu, PhotoImage
from tkinter.font import BOLD, Font
from tkinter.ttk import Label, Scale, Button

import cv2
import face_recognition
import numpy as np
import xlsxwriter
from PIL import Image, ImageTk
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import img_to_array
from tkcalendar import DateEntry


def resource_path(relative_path):
    """ Obtenha o caminho absoluto para o recurso, funciona para dev e para PyInstaller """
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath("__file__")))
    return os.path.join(base_path, relative_path)


root = tk.Tk()
root.title("Chronos")
root.iconbitmap(default=resource_path('icon/faceicon.ico'))


class Application(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.max_indexes_camera = 20
        self.menubar = tk.Menu(master)
        self.filemenu = tk.Menu(self.menubar, tearoff=False)
        self.filemenu.add_command(label="Exportar", command=self.exporta_por_data)
        self.filemenu.add_command(label="Sobre", command=self.sobre)
        self.menubar.add_cascade(label="File", menu=self.filemenu)
        self.locale = locale.getdefaultlocale()
        master.config(menu=self.menubar)
        # Configuração de detecção facial
        self.width, self.height = 800, 600
        self.MEDIA_PROB = 50.00
        self.biometria_facial_list = list()
        self.fonte_pequena, self.fonte_media = 0.4, 0.7
        self.fonte = cv2.FONT_HERSHEY_DUPLEX
        self.to_list = [['faces', 'categoria', 'probabilidade', 'data', 'hora']]
        self.category = ['young_male', 'adult_male', 'old_male', 'young_female', 'adult_female', 'old_female']
        self.category_friendly = ['Homem jovem', 'Homem adulto', 'Homem velho', 'Mulher jovem', 'Mulher adulta',
                                  'Mulher velha']
        self.category_count = {
            'young_male': 0,
            'adult_male': 0,
            'old_male': 0,
            'young_female': 0,
            'adult_female': 0,
            'old_female': 0
        }
        self.index_camera_default = 0
        self.cap = cv2.VideoCapture(self.index_camera_default)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.padding = 10
        self.iniciar_processo = False
        self.count_faces_flag = False
        self.cor_azul_rgb = (255, 50, 50)
        self.cor_verde_rgb = (0, 255, 23)
        self.cor_vermelho_rgb = (255, 0, 0)
        self.model = load_model(resource_path('processing/model_01_human_category.h5'))
        self.face_cascade = cv2.CascadeClassifier(resource_path('material/haarcascade_frontalface_default.xml'))
        # Banco de dados
        self.connection = sqlite3.connect('chronos_db.db')
        self.cursor_db = self.connection.cursor()
        # Widgets - Instanciar
        self.widget_acuracia = None
        self.option_menu = None
        self.font_title = Font(self.master, weight=BOLD)
        self.master = master
        self.menubar = tk.Menu(self.master)
        self.webcam = Label(self.master, borderwidth=1, relief="sunken")
        self.webcam.grid(row=0, column=0, padx=self.padding, pady=self.padding)
        self.genero_root = Label(self.master)
        self.row_first = Label(self.master)
        self.row_first.grid(row=1, column=0, padx=self.padding, pady=self.padding)
        self.genero_root.grid(row=3, column=0, padx=self.padding, pady=self.padding)
        # Homem label
        self.string_homem_jovem = tk.StringVar(value="Jovem: 0")
        self.string_homem_adulto = tk.StringVar(value="Adulto: 0")
        self.string_homem_velho = tk.StringVar(value="Velho: 0")
        # Mulher label
        self.string_mulher_jovem = tk.StringVar(value="Jovem: 0")
        self.string_mulher_adulta = tk.StringVar(value="Adulto: 0")
        self.string_mulher_velha = tk.StringVar(value="Velho: 0")
        # Dict genero
        self.gen_idade_dict = {
            "young_male": {"value": self.string_homem_jovem, "text": "Jovem: {}"},
            "adult_male": {"value": self.string_homem_adulto, "text": "Adulto: {}"},
            "old_male": {"value": self.string_homem_velho, "text": "Velho: {}"},
            "young_female": {"value": self.string_mulher_jovem, "text": "Jovem: {}"},
            "adult_female": {"value": self.string_mulher_adulta, "text": "Adulto: {}"},
            "old_female": {"value": self.string_mulher_velha, "text": "Velho: {}"}
        }
        # Webcam label
        self.webcam_text = tk.StringVar(value="Câmera index 0")
        self.webcam_text.trace('w', self.change_option_menu)
        self.webcam_option = dict()
        # Scale acurácia
        self.acuracia_titulo_string = tk.StringVar(value=f'Acurácia da detecção: {self.MEDIA_PROB}')
        # Button iniciar detecção facial
        self.start_detection_string = tk.StringVar(value="▶ INICIAR")
        # Inicializar Widgets
        self.return_camera_indexes()
        self.create_table()
        self.create_widgets()

    def return_camera_indexes(self):
        """
        Confere quais câmeras estão diponíveis (faz 20 verificações por padrão).
        """
        index = 0
        i = self.max_indexes_camera
        while i > 0:
            cap = cv2.VideoCapture(index)
            if cap.read()[0]:
                self.webcam_option[f'Câmera index {index}'] = index
                cap.release()
            index += 1
            i -= 1

    def create_table(self):
        query = """CREATE TABLE IF NOT EXISTS genero_idade (id INTEGER PRIMARY KEY AUTOINCREMENT, young_male number, 
        adult_male number, old_male number, young_female number, adult_female number, old_female number, 
        nu_camera number, datetime_captura TEXT) """
        self.cursor_db.execute(query)

    def insert(self, young_male, adult_male, old_male, young_female, adult_female, old_female):
        query = """INSERT INTO genero_idade (young_male, adult_male, old_male, young_female, adult_female, old_female, 
        nu_camera, datetime_captura)  VALUES (?,?,?,?,?,?,?, datetime('now'))"""
        self.cursor_db.execute(query, [young_male, adult_male, old_male, young_female, adult_female, old_female,
                                       self.index_camera_default])
        self.connection.commit()

    def create_widgets(self):
        """
        Criação de todos os widgets da janela.
        """
        self.create_widget_genero("Homem", 0, self.string_homem_jovem, self.string_homem_adulto,
                                  self.string_homem_velho)
        self.create_widget_genero("Mulher", 1, self.string_mulher_jovem, self.string_mulher_adulta,
                                  self.string_mulher_velha)
        self.create_widget_scale()
        self.create_widget_option_menu()
        self.create_widget_button(self.start_stop)
        self.show_frame()

    def create_widget_button(self, start_stop):
        """
        Criação do botão START e STOP da detecção.
        :param start_stop: é uma flag booleana para determinar se começou a detecção.
        """
        button_start_stop = Button(self.row_first, textvariable=self.start_detection_string, command=start_stop)
        button_start_stop.grid(row=1, column=0, padx=self.padding, pady=self.padding)

    def create_widget_scale(self):
        """
        Criação do widget scale de acurácia.
        """
        label_acuracia = Label(self.master, borderwidth=1, relief="groove")
        acuracia_titulo = Label(label_acuracia, textvariable=self.acuracia_titulo_string, font=self.font_title)
        acuracia_start = Label(label_acuracia, text="0.0")
        acuracia_end = Label(label_acuracia, text="100.0")
        self.widget_acuracia = Scale(label_acuracia, value=self.MEDIA_PROB, from_=0, to=100, orient=tk.HORIZONTAL,
                                     command=self.add_acuracia, length=100)
        self.widget_acuracia.set(self.MEDIA_PROB)
        acuracia_titulo.grid(row=0, column=0, columnspan=3, padx=self.padding, pady=self.padding)
        acuracia_start.grid(row=1, column=0, padx=self.padding, pady=self.padding)
        acuracia_end.grid(row=1, column=2, padx=self.padding, pady=self.padding)
        self.widget_acuracia.grid(row=2, column=0, columnspan=3, padx=self.padding, pady=self.padding)
        label_acuracia.grid(row=2, column=0, padx=self.padding, pady=self.padding)

    def create_widget_genero(self, text, column, string_jovem, string_adulto, string_velho):
        """
        Função padrão de criação de labels e texto de definição dos gêneros na janela.
        :param text: Título do gênero
        :param column: posição horizontal
        :param string_jovem: Texto '<gênero> jovem'
        :param string_adulto: Texto '<gênero> adulto'
        :param string_velho: Texto '<gênero> velho'
        """
        label_main = Label(self.genero_root, borderwidth=1, relief="groove")
        genero_titulo = Label(label_main, text=text, font=self.font_title)
        label_jovem = Label(label_main, textvariable=string_jovem)
        label_adulto = Label(label_main, textvariable=string_adulto)
        label_velho = Label(label_main, textvariable=string_velho)
        label_main.grid(row=0, column=column, padx=self.padding, pady=self.padding)
        genero_titulo.grid(row=0, column=1, padx=self.padding, pady=self.padding)
        label_jovem.grid(row=1, column=0, padx=self.padding, pady=self.padding)
        label_adulto.grid(row=1, column=1, padx=self.padding, pady=self.padding)
        label_velho.grid(row=1, column=2, padx=self.padding, pady=self.padding)

    def create_widget_option_menu(self):
        """
        Criação do widget Dropdown para selecionar câmera.
        """
        self.option_menu = OptionMenu(self.row_first, self.webcam_text, *self.webcam_option)
        self.option_menu.grid(row=1, column=1, padx=self.padding, pady=self.padding)

    def change_option_menu(self, *args):
        """
        Ao mudar no Dropdown a camera é chamado está função para pegar pegar o índice da câmera.
        :param args: informações do StringVar.
        """
        key = self.webcam_text.get()
        self.index_camera_default = self.webcam_option[key]
        self.mudar_webcam()

    def mudar_webcam(self):
        """
        Inicia a câmera com o novo índice.
        """
        self.cap = cv2.VideoCapture(self.index_camera_default)

    def start_stop(self):
        """
        Inicia a detecção ou não ao clicar no botão, o mesmo deixa os widgets de scale e dropdown desabilitados e zera
        os valores em tela e na lista de biometria facial.
        """
        titulo = "▶ INICIAR" if self.iniciar_processo else "■ PARAR"
        self.widget_acuracia["state"] = "normal" if self.iniciar_processo else "disable"
        self.option_menu["state"] = "normal" if self.iniciar_processo else "disable"
        self.start_detection_string.set(titulo)
        self.iniciar_processo = not self.iniciar_processo
        if not self.iniciar_processo:
            self.biometria_facial_list = list()
            for key, value in self.gen_idade_dict.items():
                value["value"].set(value["text"].format(0))
                self.category_count[key] = 0

    def add_acuracia(self, value=0.0):
        """
        Função para adicionar acurácia pré-definida no scale.
        :param value: Float de 0.0 a 100.0
        """
        self.MEDIA_PROB = float(value)
        self.acuracia_titulo_string.set(f'Acurácia da detecção: {round(float(value), 2)} %')

    def show_frame(self):
        """
        Função principal que fica em loop e carrega os quadros em tela, quando não houver câmera o mesmo exibe uma
        imagem estática padrão sem loop, necessário fechar aplicação para reiniciar.
        """
        conectado, frame = self.cap.read()
        if conectado:
            frame = cv2.flip(frame, 1)
            if self.iniciar_processo:
                frame = self.face_detection(frame)
            imgtk = self.ajuste_frame(frame)
            self.webcam.imgtk = imgtk
            self.webcam.configure(image=imgtk)
            # Loop for function
            self.webcam.after(10, self.show_frame)
        else:
            frame = PhotoImage(file=resource_path('images/sem_sinal.png'))
            self.webcam.imgtk = frame
            self.webcam.configure(image=frame)
            messagebox.showerror("Atenção", "Webcam não está conectado!")

    def ajuste_frame(self, frame):
        """
        Ajustes necessários no frame para carregar no TKinter Label.
        :param frame: Frame do vídeo.
        :return: Frame do vídeo configurado.
        """
        cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
        img = Image.fromarray(cv2image)
        imgtk = ImageTk.PhotoImage(image=img)
        return imgtk

    def face_detection(self, frame):
        """
        Função global de detecção facial, biometria e mapeamento de gênero e idade.
        :param frame: Frame do vídeo.
        :return: Frame do vídeo configurado com OpenCV.
        """
        cinza = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(cinza, scaleFactor=1.2, minNeighbors=5, minSize=(30, 30))
        category_count_copy = self.category_count.copy()
        if len(faces) > 0:
            for (x, y, w, h) in faces:
                frame_copy = frame.copy()
                predict = self.formatar_em_cinza_e_comprimir(cinza, x, y, h, w)
                if predict is not None:
                    resultado = np.argmax(predict)
                    prob = round(predict[resultado] * 100, 2)
                    text_box = "{}: {:.2f}%".format(self.category_friendly[resultado], prob)
                    final_frame = self.processo_biometria(frame, resultado, frame_copy, prob, x, y, h, w)
                    cv2.putText(final_frame, text_box, (x, y - 10), self.fonte, self.fonte_media, (0, 0, 0), 1,
                                cv2.LINE_AA)
                    cv2.putText(final_frame, text_box, (x, y - 10), self.fonte, self.fonte_media, (255, 255, 255), 1,
                                cv2.LINE_AA)
        self.validacao_e_insercao(category_count_copy)
        return frame

    def validacao_e_insercao(self, category_count_copy):
        """
        Faz a validação do dicionário com dados antigo 'category_count_copy' com a 'self.category_count' atualizado, se
        houver diferença é porque teve nova contagem facial e faz inserção no banco de dados e zera o dicionário
        'self.category_count'.
        :param category_count_copy: Dicionário com contagem
        """
        if category_count_copy != self.category_count:
            self.insert(**self.category_count)
            self.category_count = {key: 0 for key, value in self.category_count.items()}

    def processo_biometria(self, frame, resultado, frame_copy, prob, x, y, h, w):
        """
        Função que faz a criação da biometria facial e compara se existe na lista de biometrias já cadastradas, se não
        houver a detecção da biometria na lista e a acurácia for maior que o valor estipulado em self.MEDIA_PROB, quer
        dizer que existe um novo rosto para cadastrar com as suas devidas características; Se não houver nenhuma lista
        de biometria para comparação e a acurácia for maior que o valor estipulado em self.MEDIA_PROB é feito o primeiro
        registro de inserção; Também é feito o desenho de quadro azul ao rosto detectado e o desenho de quadro verde no
        frame do novo rosto detectado com a acurácia maior que o valor estipulado em self.MEDIA_PROB.
        :param frame: Frame para desenho com OPENCV.
        :param resultado: tag para calculo da probabilidade.
        :param frame_copy: Cópia do frame para manipulação.
        :param prob: Valor estipulado pelo Scale.
        :param x: ponto x do frame localizado o rosto.
        :param y: ponto y do frame localizado o rosto.
        :param h: ponto h do frame localizado o rosto.
        :param w: ponto w do frame localizado o rosto.
        :return: Frame desenhado.
        """
        biometria_facial = self.criando_biometria_facial(frame_copy, x, y, h, w)
        frame = cv2.rectangle(frame, (x, y), (x + w, y + h + 10), self.cor_azul_rgb, 2)
        if self.biometria_facial_list and biometria_facial is not None:
            compare_biometria = face_recognition.compare_faces(
                self.biometria_facial_list,
                biometria_facial
            )
            if True not in compare_biometria:
                if prob >= self.MEDIA_PROB:
                    self.atualizar_contagem(resultado, biometria_facial)
                    frame = cv2.rectangle(frame, (x, y), (x + w, y + h + 10), self.cor_verde_rgb, 2)
        elif prob >= self.MEDIA_PROB and biometria_facial is not None:
            self.atualizar_contagem(resultado, biometria_facial)
            frame = cv2.rectangle(frame, (x, y), (x + w, y + h + 10), self.cor_verde_rgb, 2)
        return frame

    def atualizar_contagem(self, resultado, biometria_facial):
        """
        Função agregar a função de contagem e atualização de de biometrial facial na lista self.biometria_facial_list.
        :param resultado: tag para calculo da probabilidade.
        :param biometria_facial: lista de biometrias encontradas.
        """
        self.atualizar_contagem_widget(resultado)
        self.biometria_facial_list.append(biometria_facial)

    def criando_biometria_facial(self, frame, x, y, h, w):
        """
        Criação da biometria baseando-se nos valores x, y, h, w para manipulação da matriz.
        :param frame: frame para manipulação.
        :param x: ponto x do frame localizado o rosto.
        :param y: ponto y do frame localizado o rosto.
        :param h: ponto h do frame localizado o rosto.
        :param w: ponto w do frame localizado o rosto.
        :return: 128-dimension face encoding / None
        """
        face_rgb = frame[y:y + h, x:x + w, ::-1]
        recognition = face_recognition.face_encodings(face_rgb)
        if recognition:
            return recognition[0]
        return None

    def formatar_em_cinza_e_comprimir(self, cinza, x, y, h, w):
        """
        Manipulação do frame em escala de cinza com corte na região facial para gerar predição.
        :param cinza: frame com escala de cinza COLOR_BGR2GRAY.
        :param x: ponto x do frame localizado o rosto.
        :param y: ponto y do frame localizado o rosto.
        :param h: ponto h do frame localizado o rosto.
        :param w: ponto w do frame localizado o rosto.
        :return: previsão para os dados de teste fornecido.
        """
        roi = cinza[y:y + h, x:x + w]
        roi = cv2.resize(roi, (48, 48))
        roi = roi.astype("float") / 255.0
        roi = img_to_array(roi)
        roi = np.expand_dims(roi, axis=0)
        predict = self.model.predict(roi)[0]
        return predict

    def atualizar_contagem_widget(self, resultado):
        """
        Atualiza lista e widget com contagem dos valores de gênero e idade.
        :param resultado: tag para manipular dicionário.
        """
        count = self.category_count[self.category[resultado]] + 1
        text = self.gen_idade_dict[self.category[resultado]]["text"].format(count)
        self.gen_idade_dict[self.category[resultado]]["value"].set(text)
        self.category_count[self.category[resultado]] = count

    def sobre(self):
        """
        Criação de nova janela para informações sobre o software, futuras releases e desenvolvedor.
        """
        window = tk.Tk()
        window.title("Sobre")
        window.iconbitmap(default=resource_path('icon/faceicon.ico'))
        descricao = "Essa aplicação utiliza I.A para detecção facial e mapeamento por gênero e idade de cada rosto \n" \
                    "detectado, o mesmo utiliza de biometria facial para não repetir a contagem dos rostos. Este \n" \
                    "software não salva dados de biometria facial, o mesmo só é utilizado em tempo de execução e \n" \
                    "destruído após o fim da execução, dessa maneira se mantém alinhado com a Lei Geral de Proteção\n" \
                    "de Dados Pessoais (LGPD)."
        features_futuras = "Essa aplicação ainda passará por melhorias, segue lista:\n \n" \
                           "* Melhorar o modelo de I.A.\n" \
                           "* Otimizar algoritimo de detecção facial com multithreading." \
                           "* Adicionar lógica de brilho, contraste e gamma nos frames\n" \
                           "  para melhorar o reconhecimento em ambientes mais escuros."
        descricao_autor = "Desenvovido por Marcos Vinithius"
        url_linkedin = "https://www.linkedin.com/in/vinithius/"
        url_github = "https://github.com/vinithius2"
        versao = "Versão Alpha (1.0)"
        text_descricao = Label(window, text=descricao)
        text_features_futuras = Label(window, text=features_futuras)
        text_descricao_autor = Label(window, text=descricao_autor)
        text_versao = Label(window, text=versao)
        label_contatos = Label(window, borderwidth=1, relief="raised")
        btn_linkedin = Button(label_contatos, text="Linkedin",
                              command=lambda aurl=url_linkedin: webbrowser.open_new(aurl))
        btn_github = Button(label_contatos, text="Github", command=lambda aurl=url_github: webbrowser.open_new(aurl))
        label_email = Label(label_contatos, text="marcos.vinithius@gmail.com")
        text_descricao.pack(side="top", padx=10, pady=10)
        text_features_futuras.pack(side="top", padx=10, pady=10)
        text_descricao_autor.pack(side="top", padx=10, pady=10)
        label_contatos.pack(side="top", padx=10, pady=10)
        btn_linkedin.grid(row=2, column=0, padx=10, pady=10)
        btn_github.grid(row=2, column=1, padx=10, pady=10)
        label_email.grid(row=2, column=2, padx=10, pady=10)
        text_versao.pack(side="top", padx=10, pady=10)

    def file_save(self, inicio, fim):
        """
        Abertura de dialog para exportar arquivos.
        :param inicio: Data inicial.
        :param fim: Data final.
        """
        extensions = (("Arquivo de texto", "*.txt"), ("Arquivo CSV", "*.csv"), ("Arquivo XLSX", "*.xlsx"))
        file = filedialog.asksaveasfile(mode='w', defaultextension=".csv", filetypes=extensions)
        if file is None:
            return
        query = """
            SELECT young_male, adult_male, old_male, young_female, adult_female, old_female, nu_camera, datetime_captura 
            FROM genero_idade WHERE datetime_captura BETWEEN ? AND ? ORDER BY datetime_captura ASC
        """
        self.cursor_db.execute(query, [inicio, fim])
        rows = self.cursor_db.fetchall()
        if file.name.endswith(".txt"):
            self.construir_txt(file, rows)
        elif file.name.endswith(".csv"):
            self.construir_csv(file, rows)
        elif file.name.endswith(".xlsx"):
            self.construir_xlsx(file, rows)

    def construir_txt(self, file, rows):
        """
        Exportar para o formato TXT.
        :param file: path do dialog de arquivo.
        :param rows: Número de linhas.
        """
        title = "Homem jovem, Homem adulto, Homem velho, Mulher jovem, Mulher adulta, Mulher velha, Câmera, " \
                "Data e hora\n "
        file.write(title)
        for row in rows:
            file.write(f'{row[0]}, {row[1]}, {row[2]}, {row[3]}, {row[4]}, {row[5]}, {row[6]}, {row[7]}\n')
        file.close()

    def construir_csv(self, file, rows):
        """
        Exportar para o formato CSV.
        :param file: path do dialog de arquivo.
        :param rows: Número de linhas.
        """
        with open(file.name, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            title = self.category_friendly.copy()
            title.append("Câmera")
            title.append("Data e hora")
            writer.writerow(title)
            for row in rows:
                writer.writerow(list(row))

    def construir_xlsx(self, file, rows):
        """
        Exportar para o formato XLS.
        :param file: path do dialog de arquivo.
        :param rows: Número de linhas.
        """
        workbook = xlsxwriter.Workbook(file.name)
        worksheet = workbook.add_worksheet()
        title = self.category_friendly.copy()
        title.append("Câmera")
        title.append("Data e hora")
        rows.insert(0, title)
        linha = 0
        coluna = 0
        for row in rows:
            for item in row:
                worksheet.write(linha, coluna, item)
                coluna += 1
            coluna = 0
            linha += 1
        workbook.close()

    def exporta_por_data(self):
        """
        Janela de inserção de data inicial e data final para filtrar na exportação do arquivo.
        :return:
        """
        def validation():
            datetime_inicio = datetime.strptime(calendario_inicio.get(), '%d/%m/%Y')
            datetime_fim = datetime.strptime(calendario_fim.get(), '%d/%m/%Y')
            if datetime_inicio <= datetime_fim:
                self.file_save(datetime_inicio, datetime_fim.replace(hour=23, minute=59, second=59))
            else:
                messagebox.showinfo("Atenção", "A data inicial deve ser menor ou igual que a data final.")

        top_level = tk.Tk()
        top_level.title("Exportar")
        top_level.iconbitmap(default=resource_path('icon/faceicon.ico'))
        Label(top_level, text='Data inicial').grid(row=0, column=0, padx=10, pady=10)
        Label(top_level, text='Data final').grid(row=0, column=2, padx=10, pady=10)
        calendario_inicio = DateEntry(top_level, width=12, background='darkblue', foreground='white', borderwidth=2,
                                      locale=self.locale[0])
        calendario_fim = DateEntry(top_level, width=12, background='darkblue', foreground='white', borderwidth=2,
                                   locale=self.locale[0])
        calendario_inicio.grid(row=1, column=0, padx=10, pady=10)
        calendario_fim.grid(row=1, column=2, padx=10, pady=10)
        Button(top_level, text="Exportar", command=validation).grid(row=2, column=1, padx=10, pady=5)


app = Application(master=root)
app.mainloop()
