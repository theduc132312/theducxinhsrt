import os
import json
import PySimpleGUI as sg
import google.generativeai as genai

CONFIG_FILE = os.path.expanduser("~/.theducxinhsrt_config.json")

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

def main():
    cfg = load_config()
    sg.theme("DarkBlue3")

    layout = [
        [sg.Text("Gemini API Key:"), sg.InputText(cfg.get("api_key", ""), key="API_KEY"), sg.Button("Save Key")],
        [sg.Text("File SRT:"), sg.Input(key="SRT_FILE"), sg.FileBrowse(file_types=(("SRT Files", "*.srt"),))],
        [sg.Text("Ngôn ngữ dịch:"), sg.Combo(["EN", "VI", "FR", "ES"], default_value="EN", key="LANG")],
        [sg.Text("Chế độ:"), sg.Combo(["Nhanh", "Mượt + Hài"], default_value="Nhanh", key="MODE")],
        [sg.Button("Translate"), sg.Button("Export"), sg.Button("Exit")]
    ]

    window = sg.Window("theducxinhSRT", layout)

    translated_data = ""

    while True:
        event, values = window.read()
        if event in (sg.WINDOW_CLOSED, "Exit"):
            break
        elif event == "Save Key":
            cfg["api_key"] = values["API_KEY"].strip()
            save_config(cfg)
            sg.popup("API Key đã lưu thành công.")
        elif event == "Translate":
            api_key = values["API_KEY"].strip()
            if not api_key:
                sg.popup_error("Vui lòng nhập API Key trước.")
                continue
            genai.configure(api_key=api_key)

            file_path = values["SRT_FILE"]
            if not file_path or not os.path.exists(file_path):
                sg.popup_error("Vui lòng chọn file SRT hợp lệ.")
                continue

            lang = values["LANG"]
            mode = values["MODE"]

            # Giả lập dịch (demo)
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            translated_data = f"[DỊCH {lang} - {mode}]\n" + content
            sg.popup("Dịch thành công! Bấm Export để lưu.")
        elif event == "Export":
            if not translated_data:
                sg.popup_error("Chưa có dữ liệu dịch.")
                continue
            save_path = sg.popup_get_file("Lưu file dịch", save_as=True, file_types=(("SRT Files", "*.srt"),))
            if save_path:
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(translated_data)
                sg.popup("Đã lưu file dịch.")

    window.close()

if __name__ == "__main__":
    main()
