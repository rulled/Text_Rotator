import os
import sys
import json
import urllib.request
import tempfile
import shutil
import subprocess
import ctypes
import winreg
import time
from packaging import version

class Updater:
    def __init__(self, current_version, github_api_url, asset_name="TextRotator.exe"):
        self.current_version = current_version
        self.github_api_url = github_api_url
        self.asset_name = asset_name # Это может быть "TextRotator.exe" или "TextRotator-Setup.msi" (базовое имя для MSI)
        self.temp_dir = tempfile.mkdtemp()
        self.is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
        
    def check_for_updates(self):
        """Проверяет наличие обновлений на GitHub."""
        try:
            with urllib.request.urlopen(self.github_api_url) as response:
                data = json.loads(response.read().decode('utf-8'))
                latest_version_tag = data["tag_name"] # например, "v1.0.4"
                latest_version_num = latest_version_tag.lstrip('v') # например, "1.0.4"
                
                if version.parse(latest_version_num) > version.parse(self.current_version):
                    # Определяем, ищем ли мы MSI или EXE.
                    # MSI_BASE_NAME используется для сопоставления с фактическим именем актива MSI, включающим версию.
                    # EXE_ASSET_NAME используется для прямого сопоставления.
                    
                    # Базовое имя для MSI файлов, которое передается из text_rotator.py как self.asset_name
                    # если мы ищем MSI (например, "TextRotator-Setup.msi")
                    is_looking_for_msi = "-Setup.msi" in self.asset_name 

                    for asset in data["assets"]:
                        asset_matches = False
                        if is_looking_for_msi:
                            # Для MSI ожидаем версию в имени, например, "TextRotator-1.0.4-Setup.msi"
                            # self.asset_name здесь будет базовой формой, например, "TextRotator-Setup.msi"
                            # Собираем ожидаемое имя файла MSI с версией
                            # Имя продукта (TextRotator) извлекается из self.asset_name
                            product_name_part = self.asset_name.split('-Setup.msi')[0]
                            expected_msi_name_on_github = f"{product_name_part}-{latest_version_num}-Setup.msi"
                            if asset["name"] == expected_msi_name_on_github:
                                asset_matches = True
                        else: # Ищем EXE
                            if asset["name"] == self.asset_name: # например, "TextRotator.exe"
                                asset_matches = True
                        
                        if asset_matches:
                            return {
                                "available": True,
                                "version": latest_version_num,
                                "download_url": asset["browser_download_url"],
                                "release_notes": data["body"]
                            }
                    # Если цикл завершился, соответствующий актив не найден для новой версии
                    return {"available": False, "error": "Matching asset not found for new version."}
                
                return {"available": False} # Текущая версия актуальна
        except Exception as e:
            print(f"Error in check_for_updates: {e}")
            return {"available": False, "error": str(e)}

    def download_update(self, download_url, progress_callback=None):
        """Загружает файл обновления."""
        temp_file = None
        try:
            # Имя файла из URL или self.asset_name (если URL не содержит имя)
            # Для MSI имя файла будет содержать версию, для EXE - нет
            # Мы используем имя актива из GitHub, которое уже определено в check_for_updates
            # и передано через download_url, но для сохранения файла локально нужно имя.
            # Лучше всего извлекать имя файла из URL или использовать определенное имя актива.
            # В данном случае, self.asset_name может быть базовым именем, поэтому лучше
            # взять имя из URL или определить его на основе типа.
            
            # Попытка извлечь имя файла из URL
            filename_from_url = os.path.basename(urllib.parse.urlparse(download_url).path)
            if not filename_from_url: # Если URL не содержит имя файла (маловероятно для GitHub assets)
                 # Используем self.asset_name, но это может быть неверно для MSI, если self.asset_name - базовое
                 # Однако, check_for_updates уже нашел правильный asset, так что URL должен быть к конкретному файлу
                 # Для безопасности, если имя файла не извлекается, можно использовать общий placeholder
                 filename_from_url = "downloaded_update_file"


            temp_file = os.path.join(self.temp_dir, filename_from_url)
            
            request = urllib.request.Request(
                download_url,
                headers={'User-Agent': 'TextRotator Update Agent'}
            )
            
            with urllib.request.urlopen(request, timeout=30) as response:
                total_size = int(response.info().get('Content-Length', 0))
                downloaded = 0
                chunk_size = 8192
                cancelled = False
                
                with open(temp_file, 'wb') as f:
                    while True:
                        if progress_callback and hasattr(progress_callback, 'cancelled') and progress_callback.cancelled:
                            cancelled = True
                            break
                        
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback and total_size > 0:
                            progress = int((downloaded / total_size) * 100)
                            try:
                                if progress_callback(progress): # Если callback возвращает True, отменяем
                                    cancelled = True
                                    break
                            except Exception:
                                pass # Игнорируем ошибки в callback
            
            if cancelled:
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except Exception:
                        pass
                return {"success": False, "error": "Download cancelled by user"}
            
            return {"success": True, "file_path": temp_file}
        except Exception as e:
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception:
                    pass
            return {"success": False, "error": str(e)}

    def create_updater_script(self, current_exe_path, update_file_path):
        """Создает обновляющий PowerShell скрипт с повышением прав администратора."""
        script_path = os.path.join(self.temp_dir, "updater.ps1")
        
        # Экранируем пути для использования внутри PowerShell строк
        escaped_update_file_path = update_file_path.replace("'", "''")
        escaped_current_exe_path = current_exe_path.replace("'", "''")
        
        # PowerShell скрипт для обновления
        # Исправлена ошибка: весь скрипт теперь внутри одной f-строки
        ps_script = f"""
#Requires -Version 3
# Проверяем права администратора
function Test-Admin {{
    $currentUser = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    return $currentUser.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}}

# Если нет прав администратора, перезапускаем скрипт с повышением прав
if (-not (Test-Admin)) {{
    try {{
        $scriptPath = $MyInvocation.MyCommand.Path
        Start-Process PowerShell -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`"" -Verb RunAs
        exit
    }} catch {{
        Write-Error "Не удалось запустить PowerShell с правами администратора: $_"
        exit 1
    }}
}}

# Создаем функцию для логирования
function Write-Log {{
    param([string]$message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logPath = Join-Path -Path $env:TEMP -ChildPath "TextRotatorUpdate.log"
    try {{
        "$timestamp - $message" | Out-File -Append -FilePath $logPath -Encoding UTF8
    }} catch {{
        Write-Warning "$timestamp - $message (Не удалось записать в лог: $_)"
    }}
}}

try {{
    Write-Log "Начало процесса обновления TextRotator"
    $updateFile = '{escaped_update_file_path}'
    $targetExe = '{escaped_current_exe_path}'
    $targetDir = Split-Path -Path $targetExe
    
    Write-Log "Файл обновления: $updateFile"
    Write-Log "Целевой EXE: $targetExe"
    Write-Log "Целевая директория: $targetDir"

    # Проверяем существование файла обновления
    if (-not (Test-Path -Path $updateFile -PathType Leaf)) {{
        Write-Log "Ошибка: Файл обновления не найден: $updateFile"
        throw "Файл обновления не найден: $updateFile"
    }}
    
    # Убиваем процесс, если он запущен
    $processName = [System.IO.Path]::GetFileNameWithoutExtension($targetExe)
    Write-Log "Поиск процесса: $processName"
    
    try {{
        $runningProcesses = Get-Process -Name $processName -ErrorAction SilentlyContinue
        if ($runningProcesses) {{
            Write-Log "Закрытие запущенного процесса $processName (ID: $($runningProcesses.Id -join ', '))"
            $runningProcesses | Stop-Process -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 3 # Даем время процессу завершиться
        }} else {{
            Write-Log "Процесс $processName не запущен."
        }}
    }} catch {{
        Write-Log "Ошибка при попытке остановить процесс $processName: $_"
        # Продолжаем, возможно, файл не заблокирован
    }}
    
    # Ждем, пока файл освободится (если он существует)
    $retryCount = 0
    $maxRetries = 15 # Увеличено количество попыток
    $copySuccess = $false
    
    if (Test-Path -Path $targetExe -PathType Leaf) {{
        Write-Log "Целевой файл $targetExe существует. Попытка удаления..."
        while ($retryCount -lt $maxRetries -and (-not $copySuccess)) {{
            try {{
                Remove-Item -Path $targetExe -Force -ErrorAction Stop
                Write-Log "Старый файл $targetExe успешно удален."
                # После успешного удаления можно сразу перейти к копированию
                # Но для надежности, дадим небольшую паузу
                Start-Sleep -Seconds 1 
                break # Выходим из цикла попыток удаления
            }} catch {{
                $retryCount++
                Write-Log "Ошибка удаления файла $targetExe: $_. Попытка $retryCount из $maxRetries. Ожидание 2 секунды..."
                Start-Sleep -Seconds 2
            }}
        }}
        if ($retryCount -ge $maxRetries) {{
             Write-Log "Не удалось удалить старый файл $targetExe после $maxRetries попыток."
             # Можно попробовать переименовать старый файл как запасной вариант
             $backupName = "$targetExe.old"
             try {{
                Rename-Item -Path $targetExe -NewName $backupName -Force -ErrorAction Stop
                Write-Log "Старый файл переименован в $backupName"
             }} catch {{
                Write-Log "Не удалось переименовать старый файл: $_. Обновление может завершиться ошибкой."
                # throw "Не удалось освободить целевой файл $targetExe" # Раскомментировать, если это критично
             }}
        }}
    }} else {{
        Write-Log "Целевой файл $targetExe не существует. Пропускаем удаление."
    }}

    # Создаем директорию назначения, если она не существует
    if (-not (Test-Path -Path $targetDir -PathType Container)) {{
        Write-Log "Создание директории $targetDir"
        New-Item -Path $targetDir -ItemType Directory -Force -ErrorAction Stop | Out-Null
    }}
    
    # Копируем новый файл
    Write-Log "Копирование файла обновления $updateFile в $targetExe"
    $retryCount = 0 # Сбрасываем счетчик для копирования
    $copySuccess = $false
    while ($retryCount -lt $maxRetries -and (-not $copySuccess)) {{
        try {{
            Copy-Item -Path $updateFile -Destination $targetExe -Force -ErrorAction Stop
            Write-Log "Файл обновления успешно скопирован в $targetExe"
            $copySuccess = $true
        }} catch {{
            $retryCount++
            Write-Log "Ошибка копирования файла обновления: $_. Попытка $retryCount из $maxRetries. Ожидание 2 секунды..."
            Start-Sleep -Seconds 2
        }}
    }}
    
    if (-not $copySuccess) {{
        Write-Log "Не удалось скопировать файл обновления $updateFile после $maxRetries попыток."
        throw "Не удалось скопировать файл обновления $updateFile"
    }}
    
    # Запуск обновленного приложения
    Write-Log "Запуск обновленного приложения: $targetExe"
    try {{
        Start-Process -FilePath $targetExe
        Write-Log "Приложение $targetExe успешно запущено."
    }} catch {{
        Write-Log "Ошибка запуска обновленного приложения $targetExe: $_"
        # Не бросаем исключение, чтобы скрипт мог завершить очистку
    }}
    
    # Удаление временных файлов
    Write-Log "Очистка временных файлов..."
    try {{
        Remove-Item -Path $updateFile -Force -ErrorAction SilentlyContinue
        Write-Log "Временный файл обновления $updateFile удален."
    }} catch {{
        Write-Log "Ошибка удаления временного файла $updateFile: $_"
    }}
    
    # Самоудаление скрипта обновления (не всегда надежно, но стоит попробовать)
    # $currentScriptPath = $MyInvocation.MyCommand.Path
    # Write-Log "Попытка самоудаления скрипта: $currentScriptPath"
    # try {{
    #     Start-Sleep -Seconds 2
    #     Remove-Item -Path $currentScriptPath -Force -ErrorAction SilentlyContinue
    #     # Этот лог уже не будет записан, так как файл скрипта должен быть удален
    # }} catch {{
    #     Write-Log "Ошибка самоудаления скрипта $currentScriptPath: $_"
    # }}
    
    Write-Log "Процесс обновления TextRotator завершен."
}} catch {{
    Write-Log "КРИТИЧЕСКАЯ ОШИБКА процесса обновления TextRotator: $($_.Exception.Message)"
    Write-Error "Произошла ошибка во время обновления: $($_.Exception.Message)"
    # Попытка очистки временного файла обновления даже при ошибке
    if (Test-Path -Path $updateFile -PathType Leaf) {{
        try {{ Remove-Item -Path $updateFile -Force -ErrorAction SilentlyContinue }} catch {{}}
    }}
    exit 1
}}
exit 0
"""
        try:
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(ps_script)
            return script_path
        except Exception as e:
            print(f"Error writing updater script: {e}")
            return None

    def install_update(self, current_exe_path, update_file_path):
        """
        Запускает процесс установки обновления.
        Если update_file_path - это .msi, запускает его через os.startfile и завершает программу.
        Если update_file_path - это .exe, использует PowerShell скрипт.
        """
        try:
            if not os.path.exists(update_file_path):
                return {"success": False, "error": f"Файл обновления не найден: {update_file_path}"}
            
            ext = os.path.splitext(update_file_path)[-1].lower()
            
            if ext == '.msi':
                try:
                    # Для MSI просто запускаем установщик. Windows Installer сам обработает обновление.
                    # Приложение должно будет закрыться, чтобы MSI мог заменить файлы.
                    os.startfile(update_file_path)
                    # Важно: приложение должно быть закрыто ДО или ВО ВРЕМЯ запуска MSI.
                    # Вызываем sys.exit() здесь, чтобы закрыть текущее приложение.
                    print("Запуск MSI установщика и выход из приложения...")
                    sys.exit(0) 
                    # return {"success": True} # Этот код не будет достигнут из-за sys.exit()
                except Exception as e:
                    return {"success": False, "error": f"Ошибка запуска MSI: {str(e)}"}
            else: # .exe обновление (портативное)
                updater_script_path = self.create_updater_script(current_exe_path, update_file_path)
                if not updater_script_path or not os.path.exists(updater_script_path):
                    return {"success": False, "error": "Не удалось создать скрипт обновления PowerShell."}
                
                try:
                    # Запускаем PowerShell скрипт. Он сам запросит повышение прав, если нужно.
                    # CREATE_NEW_CONSOLE гарантирует, что окно PowerShell не будет привязано к текущему процессу.
                    subprocess.Popen(
                        ["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", updater_script_path],
                        creationflags=subprocess.CREATE_NEW_CONSOLE,
                        stdout=subprocess.DEVNULL, # Скрываем вывод PowerShell
                        stderr=subprocess.DEVNULL
                    )
                    print(f"Запущен скрипт обновления: {updater_script_path}")
                    # После запуска скрипта обновления, текущее приложение должно завершиться,
                    # чтобы скрипт мог заменить его файлы.
                    sys.exit(0) # Завершаем текущее приложение
                    # return {"success": True} # Не будет достигнут
                except Exception as e:
                    return {"success": False, "error": f"Ошибка запуска скрипта обновления: {str(e)}"}
        except Exception as e:
            # Очистка временных файлов в случае непредвиденной ошибки
            self.cleanup_temp_files()
            return {"success": False, "error": f"Непредвиденная ошибка в install_update: {str(e)}"}

    def check_msi_installation(self):
        """Проверяет, установлено ли приложение через MSI, и возвращает путь установки, если да."""
        uninstall_paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", winreg.KEY_READ | winreg.KEY_WOW64_64KEY),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall", winreg.KEY_READ | winreg.KEY_WOW64_32KEY), # Явно для 32-bit на 64-bit
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", winreg.KEY_READ)
        ]
        # Имя, которое отображается в "Установка и удаление программ" (должно совпадать с Product.wxs)
        # Предположим, что DisplayName в вашем WXS это "Text Rotator"
        target_display_name = "Text Rotator" 

        for hkey, path, flags in uninstall_paths:
            try:
                with winreg.OpenKey(hkey, path, 0, flags) as key:
                    for i in range(winreg.QueryInfoKey(key)[0]):
                        subkey_name = winreg.EnumKey(key, i)
                        with winreg.OpenKey(key, subkey_name, 0, flags) as subkey:
                            try:
                                display_name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                                if display_name == target_display_name:
                                    install_location = winreg.QueryValueEx(subkey, "InstallLocation")[0]
                                    return True, install_location
                            except FileNotFoundError: # Если DisplayName или InstallLocation отсутствует
                                pass
                            except Exception: # Другие ошибки чтения значения
                                pass
            except FileNotFoundError: # Если ключ Uninstall не найден
                pass
            except Exception: # Другие ошибки открытия ключа
                pass
        return False, None
    
    def add_to_startup(self, app_path, app_name="TextRotator"):
        """Добавляет приложение в автозапуск Windows."""
        try:
            if not os.path.exists(app_path):
                print(f"Предупреждение: Файл для автозапуска {app_path} не существует.")
                # Можно вернуть False или продолжить, если предполагается, что файл будет создан позже
                # return False 
            
            # Ключ реестра для автозапуска текущего пользователя
            key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
            
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, f'"{app_path}"') # Путь в кавычках
            return True
        except Exception as e:
            print(f"Ошибка добавления в автозапуск: {e}")
            return False
    
    def remove_from_startup(self, app_name="TextRotator"):
        """Удаляет приложение из автозапуска Windows."""
        try:
            key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
                try:
                    winreg.DeleteValue(key, app_name)
                except FileNotFoundError:
                    # Если значение не найдено, считаем, что его уже нет (успех)
                    print(f"Запись автозапуска '{app_name}' не найдена, удаление не требуется.")
                    pass 
            return True
        except Exception as e:
            print(f"Ошибка удаления из автозапуска: {e}")
            return False
            
    def cleanup_temp_files(self):
        """Очищает временные файлы, созданные во время обновления."""
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir, ignore_errors=True) # ignore_errors=True для большей надежности
            return True
        except Exception as e:
            print(f"Ошибка при очистке временных файлов: {e}")
            return False

