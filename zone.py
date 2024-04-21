import tkinter as tk


class TransparentAreaSelector:
    def __init__(self, root):
        self.root = root
        self.root.title("Sélection de Zone")
        # Rendre la fenêtre semi-transparente
        self.root.attributes('-alpha', 0.3)
        # Garde la fenêtre au-dessus des autres
        self.root.attributes('-topmost', True)

        # Définir la taille initiale de la fenêtre pour couvrir tout l'écran
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        self.root.geometry(f"{screen_width}x{screen_height}+0+0")

        self.start_x = None
        self.start_y = None
        self.rect = None

        # Créer un canvas pour dessiner la zone de sélection
        self.canvas = tk.Canvas(root, cursor="cross", bg='grey')
        self.canvas.pack(fill="both", expand=True)

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

    def on_press(self, event):
        # Sauvegarder la position de départ
        self.start_x = event.x
        self.start_y = event.y
        # Créer un rectangle (sera redimensionné lors du drag)
        if not self.rect:
            self.rect = self.canvas.create_rectangle(
                self.start_x, self.start_y, self.start_x, self.start_y, outline='red')

    def on_drag(self, event):
        # Mettre à jour les dimensions du rectangle lors du drag
        curX, curY = event.x, event.y
        self.canvas.coords(self.rect, self.start_x, self.start_y, curX, curY)

    def on_release(self, event):
        # Afficher les coordonnées de la zone sélectionnée
        end_x, end_y = event.x, event.y
        print("Zone sélectionnée: ", (self.start_x, self.start_y, end_x, end_y))
        # Optionnel: ici vous pouvez fermer la fenêtre ou laisser l'utilisateur ajuster la sélection
        # self.root.destroy()


def main():
    root = tk.Tk()
    app = TransparentAreaSelector(root)
    root.mainloop()


if __name__ == "__main__":
    main()
