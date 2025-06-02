import sys
import csv
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox, QFileDialog, QAction, QDockWidget, QScrollArea,
    QTabWidget, QInputDialog, QHBoxLayout, QStatusBar
)
from PyQt5.QtCore import Qt
from PyQt5.QtSql import QSqlDatabase, QSqlQuery
from PyQt5.QtGui import QClipboard


class DatabaseBuku:
    def __init__(self, nama_db="perpustakaan.sql"):
        self.db = QSqlDatabase.addDatabase("QSQLITE")
        self.db.setDatabaseName(nama_db)
        self.db.open()
        self._buat_tabel()

    def _buat_tabel(self):
        query = QSqlQuery()
        query.exec("""
            CREATE TABLE IF NOT EXISTS Buku (
                ID INTEGER PRIMARY KEY AUTOINCREMENT,
                Judul TEXT NOT NULL,
                Pengarang TEXT NOT NULL,
                Tahun INTEGER NOT NULL
            );
        """)

    def tambah(self, judul, pengarang, tahun):
        if not (judul and pengarang and tahun.isdigit()):
            return False
        query = QSqlQuery()
        query.prepare("INSERT INTO Buku (Judul, Pengarang, Tahun) VALUES (?, ?, ?)")
        query.addBindValue(judul)
        query.addBindValue(pengarang)
        query.addBindValue(int(tahun))
        return query.exec()

    def ubah(self, kolom, nilai, id_buku):
        query = QSqlQuery()
        query.prepare(f"UPDATE Buku SET {kolom} = ? WHERE ID = ?")
        query.addBindValue(nilai)
        query.addBindValue(id_buku)
        return query.exec()

    def hapus(self, id_buku):
        query = QSqlQuery()
        query.prepare("DELETE FROM Buku WHERE ID = ?")
        query.addBindValue(id_buku)
        return query.exec()

    def ambil(self, keyword=""):
        query = QSqlQuery()
        if keyword:
            query.prepare("SELECT * FROM Buku WHERE Judul LIKE ?")
            query.addBindValue(f"%{keyword}%")
        else:
            query.prepare("SELECT * FROM Buku")
        query.exec()
        return query

    def ekspor_csv(self, path):
        query = QSqlQuery("SELECT * FROM Buku")
        with open(path, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["ID", "Judul", "Pengarang", "Tahun"])
            while query.next():
                writer.writerow([query.value(i) for i in range(4)])


class TabelBuku(QTableWidget):
    def __init__(self, db: DatabaseBuku):
        super().__init__()
        self.db = db
        self.columns = ["ID", "Judul", "Pengarang", "Tahun"]
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(self.columns)
        self.keyword = ""
        self.load_data()
        self.cellDoubleClicked.connect(self.edit_data)

    def load_data(self):
        self.blockSignals(True)
        hasil = self.db.ambil(self.keyword)
        data = []
        while hasil.next():
            data.append([hasil.value(i) for i in range(4)])
        self.setRowCount(len(data))
        for i, row in enumerate(data):
            for j, val in enumerate(row):
                item = QTableWidgetItem(str(val))
                if j == 0:
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.setItem(i, j, item)
        self.resizeColumnsToContents()
        self.horizontalHeader().setStretchLastSection(True)
        self.blockSignals(False)

    def filter_data(self, keyword):
        self.keyword = keyword
        self.load_data()

    def edit_data(self, row, col):
        if col == 0:
            return
        id_buku = int(self.item(row, 0).text())
        kolom = self.columns[col]
        nilai_lama = self.item(row, col).text()
        nilai_baru, ok = QInputDialog.getText(self, f"Edit {kolom}", f"{kolom}:", QLineEdit.Normal, nilai_lama)
        if ok and nilai_baru.strip():
            self.db.ubah(kolom, nilai_baru.strip(), id_buku)
            self.load_data()


class FormBuku(QDockWidget):
    def __init__(self, parent, db: DatabaseBuku, table: TabelBuku):
        super().__init__("Form Buku")
        self.parent = parent
        self.db = db
        self.table = table

        # Input fields
        self.input_judul = QLineEdit()
        self.input_pengarang = QLineEdit()
        self.input_tahun = QLineEdit()
        self.input_cari = QLineEdit()
        self.input_cari.setPlaceholderText("Cari judul...")
        self.input_cari.textChanged.connect(lambda: self.table.filter_data(self.input_cari.text()))

        # Buttons
        tombol_tempel = QPushButton("Tempel dari Clipboard")
        tombol_simpan = QPushButton("Simpan Buku")
        tombol_hapus = QPushButton("Hapus Buku")

        tombol_tempel.clicked.connect(self.paste_clipboard)
        tombol_simpan.clicked.connect(self.simpan_data)
        tombol_hapus.clicked.connect(self.hapus_data)

        # Form Layout
        form_layout = QFormLayout()
        form_layout.addRow("Judul", self.input_judul)
        form_layout.addRow("Pengarang", self.input_pengarang)
        form_layout.addRow("Tahun", self.input_tahun)
        form_layout.addRow(tombol_tempel)
        form_layout.addRow("Cari", self.input_cari)
        form_layout.addRow(tombol_simpan)
        form_layout.addRow(tombol_hapus)

        form_widget = QWidget()
        form_widget.setLayout(form_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(form_widget)

        self.setWidget(scroll)
        self.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)

    def paste_clipboard(self):
        teks = QApplication.clipboard().text()
        data = [x.strip() for x in teks.split(",")]
        if len(data) >= 3:
            self.input_judul.setText(data[0])
            self.input_pengarang.setText(data[1])
            self.input_tahun.setText(data[2])

    def simpan_data(self):
        judul = self.input_judul.text().strip()
        pengarang = self.input_pengarang.text().strip()
        tahun = self.input_tahun.text().strip()
        if self.db.tambah(judul, pengarang, tahun):
            self.input_judul.clear()
            self.input_pengarang.clear()
            self.input_tahun.clear()
            self.table.load_data()
        else:
            QMessageBox.warning(self, "Kesalahan", "Isi semua kolom. Tahun harus berupa angka.")

    def hapus_data(self):
        baris = self.table.currentRow()
        if baris < 0:
            QMessageBox.warning(self, "Peringatan", "Pilih baris yang ingin dihapus.")
            return
        id_buku = int(self.table.item(baris, 0).text())
        konfirmasi = QMessageBox.question(
            self, "Konfirmasi", f"Hapus buku ID {id_buku}?",
            QMessageBox.Yes | QMessageBox.No
        )
        if konfirmasi == QMessageBox.Yes:
            self.db.hapus(id_buku)
            self.table.load_data()


class AplikasiBuku(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Manajemen Buku - Lalu Maulana Rizki Hidayat (F1D02310118)")
        self.setGeometry(200, 100, 900, 600)
        self.db = DatabaseBuku()
        self._setup_ui()
        self._setup_menu()
        self._setup_statusbar()

    def _setup_ui(self):
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Tab Data Buku
        self.tabel = TabelBuku(self.db)
        tab_data = QWidget()
        layout_data = QVBoxLayout()
        layout_data.addWidget(self.tabel)
        tab_data.setLayout(layout_data)
        self.tabs.addTab(tab_data, "Data Buku")

        # Tab Ekspor
        tab_export = QWidget()
        layout_export = QVBoxLayout()
        label = QLabel("Klik untuk ekspor data ke file CSV.")
        tombol_export = QPushButton("Ekspor ke CSV")
        tombol_export.clicked.connect(self.ekspor_csv)
        layout_export.addWidget(label)
        layout_export.addWidget(tombol_export)
        tab_export.setLayout(layout_export)
        self.tabs.addTab(tab_export, "Ekspor")

        # Form Dock
        self.form = FormBuku(self, self.db, self.tabel)
        self.addDockWidget(Qt.TopDockWidgetArea, self.form)

    def _setup_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        edit_menu = menubar.addMenu("Edit")

        file_menu.addAction(QAction("Simpan", self, triggered=self.form.simpan_data))
        file_menu.addAction(QAction("Ekspor ke CSV", self, triggered=self.ekspor_csv))
        file_menu.addAction(QAction("Keluar", self, triggered=self.close))

        edit_menu.addAction(QAction("Cari Judul", self, triggered=lambda: self.tabel.filter_data(self.form.input_cari.text())))
        edit_menu.addAction(QAction("Hapus Data", self, triggered=self.form.hapus_data))

    def _setup_statusbar(self):
        status = QStatusBar()
        status.showMessage("Lalu Maulana Rizki Hidayat - F1D02310118")
        self.setStatusBar(status)

    def ekspor_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Simpan CSV", "", "CSV Files (*.csv)")
        if path:
            if not path.endswith(".csv"):
                path += ".csv"
            self.db.ekspor_csv(path)
            QMessageBox.information(self, "Sukses", "Data berhasil diekspor ke CSV.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AplikasiBuku()
    window.show()
    sys.exit(app.exec())
