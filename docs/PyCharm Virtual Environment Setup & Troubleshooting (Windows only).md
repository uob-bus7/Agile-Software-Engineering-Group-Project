---
aliases:
created: 2026-01-22T11:56:18
edited: 2026-01-22T13:52:04
---

## 0. Before You Do Anything: Open the Right Terminal in the Right Folder

#### 0.1 Confirm You Are in the Project Folder

```powershell
pwd
```

#### 0.2 List Files so You Can See what you’re Working with

```powershell
ls
```

You want to see your project files here (for example `requirements.txt`, `app.py`, etc.).

---

## 1. The Scenario You Are in

#### Scenario A: You Are Creating Your Own .venv (recommended)

- You create `.venv` yourself (PyCharm UI OR command line).
- PyCharm interpreter is set to `.venv`.
- You can usually run `pip` and `flask` directly _after activation/interpreter selection_.

#### Scenario B: You Unzipped/Inherited Someone else’s Environment (or You don’t Trust PATH)

- You extracted a zip and it came with a `.venv` (or you are not sure what’s active).

---

## 2. Create the Virtual Environment

#### 2.1 Create in PyCharm (UI method)

- Add New Interpreter → Add Local Interpreter → Generate new → OK
- Make sure to choose the appropriate Base Python
- Do not tick anything else

Once that is set, PyCharm’s terminal often behaves correctly without extra steps.

#### 2.2 Create via PowerShell (command method)

```powershell
python -m venv .venv
```

#### 2.3 `ensurepip`

`ensurepip` bootstraps/repairs **pip inside the current Python interpreter** (including inside a .venv). You use it when:

- `pip` is missing
- `python -m pip …` fails because pip is not installed in that interpreter

#### 2.4 Use it

```powershell
python -m ensurepip --upgrade
```

#### 2.5 Then Immediately Verify Pip is Available

```powershell
python -m pip --version
```

---

## 3. Activate the Virtual Environment

#### 3.1 PowerShell Activation for Scenario B (two Working forms)

**Robust (always works if the file exists):**

```powershell
.venv\bin\Activate.ps1
```

**Your “Activate works on its own” form (use if it works in your shell/PyCharm terminal):**

```powershell
.venv\bin\Activate
```

If `.venv\bin\Activate` works in your setup, keep using it. The `.ps1` path form is just the universal fallback.

#### 3.2 PowerShell Activation for Scenario A (Not Really Needed unless you creat the .venv via a command line)

```powershell
.venv\Scripts\Activate
```

#### 3.3 Deactivate

```powershell
deactivate
```

---

## 4. Checks (so You Know what Python You Are Actually using)

#### 4.1 Find What is Being Resolved

```powershell
where.exe python
```

```powershell
where.exe pip
```

```powershell
where.exe flask
```

#### 4.2 Check Versions - Scenario A

```powershell
python --version
```

```powershell
pip --version
```

```powershell
flask --version
```

#### 4.3 Check Versions - Scenario B

```powershell
python -m python --version
```

```powershell
python -m pip --version
```

```powershell
python -m flask --version
```

If `pip` or `flask` commands fail, don’t guess. Use the repair steps below.

---

## 5. Installing Dependencies (For the Previously Defined Scenarios)

#### 5.1 Scenario A

If you created the .venv yourself you can do:

```powershell
pip install -r requirements.txt
```

Or for flask:

```powershell
pip install flask
```

#### 5.2 Scenario B

Use:

```powershell
python -m pip install -r requirements.txt
```

Or:

```powershell
python -m pip install flask
```

#### 5.3 Show what’s Installed

```powershell
python -m pip list
```

---

## 6. Running Flask

```powershell
flask run
```

**If this doesn't work jump to the next step.**

---

## 7. Delete The Environment and Start from Scratch

```powershell
Remove-Item -Recurse -Force .venv
```

**Now go back to step 2**
