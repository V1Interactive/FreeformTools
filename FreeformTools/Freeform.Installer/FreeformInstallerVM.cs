namespace Freeform.Installer
{
  using Freeform.Core.UI;
  using Microsoft.Win32;
  using System;
  using System.Collections.Generic;
  using System.Collections.ObjectModel;
  using System.ComponentModel;
  using System.IO;
  using System.Linq;
  using System.Text;
  using System.Threading.Tasks;
  using System.Windows.Data;
  using System.Windows.Forms;

  enum InstallerState { GetToolsPath, GetMayaPath, CheckToolsPaths, Recap }
  enum MayaVersion { Maya_2019, Maya_2020, Maya_2022, Maya_2023, Custom }

  public class FreeformInstallerVM : ViewModelBase
  {
    public RelayCommand NextStepCommand { get; set; }
    public RelayCommand PreviousStepCommand { get; set; }
    public RelayCommand SetToolsPathCommand { get; set; }
    public RelayCommand SetMayaPathCommand { get; set; }
    public RelayCommand SetPythonPackageCommand { get; set; }

    Dictionary<MayaVersion, string> PythonVersionDict;


    InstallerState _installerState;
    InstallerState InstallerState {
      get { return _installerState; }
      set
      {
        _installerState = value;
        RaisePropertyChanged("InstallerState");
      }
    }


    ObservableCollection<string> _dccNameList;
    public ObservableCollection<string> DccNameList
    {
      get{
        return _dccNameList;
      }
      set{
        _dccNameList = value;
        RaisePropertyChanged("DccNameList");
      }
    }

    string _selectedDccName;
    public string SelectedDccName
    {
      get { return _selectedDccName; }
      set
      {
        _selectedDccName = value;

        MayaPathReadOnly = true;
        if (SelectedDccName == "Custom")
          MayaPathReadOnly = false;

        switch (_selectedDccName) {
          case "Maya_2019":
            MayaPath = (string)Registry.GetValue("HKEY_LOCAL_MACHINE\\SOFTWARE\\Autodesk\\Maya\\2019\\Setup\\InstallPath", "MAYA_INSTALL_LOCATION", string.Empty);
            break;
          case "Maya_2020":
            MayaPath = (string)Registry.GetValue("HKEY_LOCAL_MACHINE\\SOFTWARE\\Autodesk\\Maya\\2020\\Setup\\InstallPath", "MAYA_INSTALL_LOCATION", string.Empty);
            break;
          case "Maya_2022":
            MayaPath = (string)Registry.GetValue("HKEY_LOCAL_MACHINE\\SOFTWARE\\Autodesk\\Maya\\2022\\Setup\\InstallPath", "MAYA_INSTALL_LOCATION", string.Empty);
            break;
          case "Maya_2023":
            MayaPath = (string)Registry.GetValue("HKEY_LOCAL_MACHINE\\SOFTWARE\\Autodesk\\Maya\\2023\\Setup\\InstallPath", "MAYA_INSTALL_LOCATION", string.Empty);
            break;
          default:
            MayaPath = string.Empty;
            break;
        }

        if (MayaPath == null) {
          MayaPath = "< " + _selectedDccName + " is not installed >";
        }

        RaisePropertyChanged("SelectedDccName");
      }
    }

    MayaVersion MayaInstallVersion
    {
      get
      {
        if (SelectedDccName == "Custom") {
          if (Directory.Exists(MayaPath)){
            string mayaFolder = Path.GetFileName(MayaPath);
            string dccName = mayaFolder.Insert(4, "_");
            if (Enum.IsDefined(typeof(MayaVersion), dccName)){
              return (MayaVersion)Enum.Parse(typeof(MayaVersion), dccName);
            }
          }
        }
        return (MayaVersion)Enum.Parse(typeof(MayaVersion), SelectedDccName);
      }
    }

    string MayaVersionNumber
    {
      get { return MayaInstallVersion.ToString().Split('_').Last(); }
    }

    string _toolsPath;
    public string ToolsPath
    {
      get { return _toolsPath; }
      set
      {
        _toolsPath = value;
        RaisePropertyChanged("ToolsPath");
      }
    }

    string _mayaPath;
    public string MayaPath
    {
      get { return _mayaPath; }
      set
      {
        _mayaPath = value;
        RaisePropertyChanged("MayaPath");
      }
    }

    string _pythonPackageDirectory;
    public string PythonPackageDirectory
    {
      get { return _pythonPackageDirectory; }
      set
      {
        _pythonPackageDirectory = value;
        RaisePropertyChanged("PythonPackageDirectory");
        RaisePropertyChanged("PythonPackageFolder");
      }
    }

    public string PythonPackageFolder
    {
      get { return Path.GetFileName(PythonPackageDirectory); }
    }

    string _advanceButtonText;
    public string AdvanceButtonText
    {
      get { return _advanceButtonText; }
      set
      {
        _advanceButtonText = value;
        RaisePropertyChanged("AdvanceButtonText");
      }
    }

    string _userSetupPath;
    public string UserSetupPath
    {
      get { return _userSetupPath; }
      set
      {
        _userSetupPath = value;
        RaisePropertyChanged("UserSetupPath");
      }
    }

    string _sitePackagesPath;
    public string SitePackagesPath
    {
      get { return _sitePackagesPath; }
      set
      {
        _sitePackagesPath = value;
        RaisePropertyChanged("SitePackagesPath");
      }
    }

    bool _previousVisible;
    public bool PreviousVisible
    {
      get { return _previousVisible; }
      set
      {
        _previousVisible = value;
        RaisePropertyChanged("PreviousVisible");
      }
    }

    bool _mayaPathReadOnly;
    public bool MayaPathReadOnly
    {
      get { return _mayaPathReadOnly; }
      set 
      {
        _mayaPathReadOnly = value;
        RaisePropertyChanged("MayaPathReadOnly");
      }
    }

    bool _getToolsPathVisible;
    public bool GetToolsPathVisible
    {
      get { return _getToolsPathVisible; }
      set
      {
        _getToolsPathVisible = value;
        RaisePropertyChanged("GetToolsPathVisible");
      }
    }

    bool _getMayaPathVisible;
    public bool GetMayaPathVisible
    {
      get { return _getMayaPathVisible; }
      set
      {
        _getMayaPathVisible = value;
        RaisePropertyChanged("GetMayaPathVisible");
      }
    }

    bool _checkToolsPathsVisible;
    public bool CheckToolsPathsVisible
    {
      get { return _checkToolsPathsVisible; }
      set
      {
        _checkToolsPathsVisible = value;
        RaisePropertyChanged("CheckToolsPathsVisible");
      }
    }

    bool _recapVisible;
    public bool RecapVisible
    {
      get { return _recapVisible; }
      set
      {
        _recapVisible = value;
        RaisePropertyChanged("RecapVisible");
      }
    }

    bool _installVallid;
    public bool InstallVallid
    {
      get { return _installVallid; }
      set
      {
        _installVallid = value;
        RaisePropertyChanged("InstallVallid");
      }
    }



    public FreeformInstallerVM()
    {
      PythonVersionDict = new Dictionary<MayaVersion, string>() { {MayaVersion.Maya_2019, "2.7"},
                                                                  {MayaVersion.Maya_2020, "2.7"},
                                                                  {MayaVersion.Maya_2022, "3.7"},
                                                                  {MayaVersion.Maya_2023, "3.9"} };

      InstallerState = InstallerState.GetToolsPath;

      DccNameList = new ObservableCollection<string>(Enum.GetNames(typeof(MayaVersion)));
      SelectedDccName = MayaVersion.Maya_2019.ToString();
      MayaPathReadOnly = true;
      PreviousVisible = false;

      GetToolsPathVisible = true;
      GetMayaPathVisible = false;
      CheckToolsPathsVisible = false;
      RecapVisible = false;
      InstallVallid = true;
      AdvanceButtonText = "Next >";

      string exeFilePath = System.Reflection.Assembly.GetExecutingAssembly().Location;
      string exeDirectory = Path.GetDirectoryName(exeFilePath);

      DirectoryInfo dirInfo = new DirectoryInfo(exeDirectory);
      ToolsPath = dirInfo.Parent.FullName;

      SetToolsPathCommand = new RelayCommand(SetToolsPathCall);
      SetMayaPathCommand = new RelayCommand(SetMayaPathCall);
      SetPythonPackageCommand = new RelayCommand(SetPythonPackageCall);

      NextStepCommand = new RelayCommand(NextStepCall);
      PreviousStepCommand = new RelayCommand(PreviousStepCall);
    }

    private void VerifyInstall()
    {
      bool dirExists = Directory.Exists(ToolsPath);
      bool mayaExists = Directory.Exists(MayaPath);
      bool pythonExists = Directory.Exists(PythonPackageDirectory);

      InstallVallid = dirExists && mayaExists && pythonExists;
    }

    private void RunInstall()
    {
      Environment.SetEnvironmentVariable("V1TOOLSROOT", ToolsPath, EnvironmentVariableTarget.User);
      string myDocuments = Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments);
      UserSetupPath = Path.Join(myDocuments, "maya", MayaVersionNumber, "scripts");

      if (MayaVersionNumber == "2023")
      {
        SitePackagesPath = Path.Join(UserSetupPath, "site-packages");
      }
      else if (MayaVersionNumber == "2022")
      {
        SitePackagesPath = Path.Join(MayaPath, "Python37", "Lib", "site-packages");
      }
      else
      {
        SitePackagesPath = Path.Join(MayaPath, "Python", "Lib", "site-packages");
      }

      // Copy the userSetup.py file to the Maya /scripts directory
      string userSetupPyPath = Path.Join(PythonPackageDirectory, "userSetup.py");
      string userSetupPyCopyPath = Path.Join(UserSetupPath, "userSetup.py");
      if(File.Exists(userSetupPyPath)){
        File.Copy(userSetupPyPath, userSetupPyCopyPath, true);
      }

      string defaultConfigPath = Path.Join(ToolsPath, "default_config", "tools_config.json");
      string configPath = Path.Join(ToolsPath, "tools_config.json");
      File.Copy(defaultConfigPath, configPath, true);

      // Copy the pythonnet directory to the site-packages directory
      string pythonnetDirectory = string.Empty;
      foreach (string subDir in Directory.GetDirectories(PythonPackageDirectory))
      {
        if (subDir.Contains("pythonnet"))
        {
          pythonnetDirectory = subDir;
        }
      }

      CopyFilesRecursively(pythonnetDirectory, SitePackagesPath);
    }

    private static void CopyFilesRecursively(string sourcePath, string targetPath)
    {
      //Now Create all of the directories
      foreach (string dirPath in Directory.GetDirectories(sourcePath, "*", SearchOption.AllDirectories))
      {
        _ = Directory.CreateDirectory(dirPath.Replace(sourcePath, targetPath));
      }

      //Copy all the files & Replaces any files with the same name
      foreach (string newPath in Directory.GetFiles(sourcePath, "*.*", SearchOption.AllDirectories))
      {
        File.Copy(newPath, newPath.Replace(sourcePath, targetPath), true);
      }
    }


    private void GetPythonPackage()
    {
      PythonPackageDirectory = string.Empty;
      string packagesRoot = Path.Join(ToolsPath, "packages");
      string pythonVersion = PythonVersionDict.GetValueOrDefault(MayaInstallVersion);

      if(Directory.Exists(packagesRoot) && pythonVersion != null)
      {
        foreach (string subDir in Directory.GetDirectories(packagesRoot))
        {
          if (subDir.Contains(pythonVersion))
          {
            PythonPackageDirectory = subDir;
          }
        }
      }
      if(PythonPackageDirectory == string.Empty){
        PythonPackageDirectory = "< Missing >";
      }
    }

    public void SetToolsPathCall(object sender)
    {
      string chosenPath = GetPath(ToolsPath);
      if (chosenPath != string.Empty)
      {
        ToolsPath = chosenPath;
      }
    }

    public void SetMayaPathCall(object sender)
    {
      string chosenPath = GetPath(Environment.ExpandEnvironmentVariables("%ProgramW6432%"));
      if (chosenPath != string.Empty)
      {
        MayaPath = chosenPath;
      }
    }

    public void SetPythonPackageCall(object sender)
    {
      string chosenPath = GetPath(ToolsPath);
      if (chosenPath != string.Empty)
      {
        PythonPackageDirectory = chosenPath;
      }
      VerifyInstall();
    }

    public string GetPath(string startPath)
    {
      string returnPath = string.Empty;
      using (FolderBrowserDialog fbd = new FolderBrowserDialog())
      {
        fbd.Description = "Pick Directory";
        fbd.SelectedPath = startPath;
        DialogResult result = fbd.ShowDialog();

        if (result == DialogResult.OK && !string.IsNullOrWhiteSpace(fbd.SelectedPath))
        {
          returnPath = fbd.SelectedPath;
        }
      }
      return returnPath;
    }

    private void NextStepCall(object sender){
      switch (InstallerState)
      {
        case InstallerState.GetToolsPath:
          PreviousVisible = true;
          InstallerState = InstallerState.GetMayaPath;
          GetToolsPathVisible = false;
          GetMayaPathVisible = true;
          break;
        case InstallerState.GetMayaPath:
          GetPythonPackage();
          InstallerState = InstallerState.CheckToolsPaths;
          VerifyInstall();
          AdvanceButtonText = "Install";
          GetMayaPathVisible = false;
          CheckToolsPathsVisible = true;
          break;
        case InstallerState.CheckToolsPaths:
          InstallerState = InstallerState.Recap;
          RunInstall();
          AdvanceButtonText = "Finished";
          CheckToolsPathsVisible = false;
          RecapVisible = true;
          PreviousVisible = false;
          break;
        case InstallerState.Recap:
          Close();
          break;
        default:
          break;
      }
    }

    private void PreviousStepCall(object sender){
      switch (InstallerState)
      {
        case InstallerState.GetToolsPath:
          break;
        case InstallerState.GetMayaPath:
          PreviousVisible = false;
          InstallerState = InstallerState.GetToolsPath;
          GetToolsPathVisible = true;
          GetMayaPathVisible = false;
          break;
        case InstallerState.CheckToolsPaths:
          InstallerState = InstallerState.GetMayaPath;
          AdvanceButtonText = "Next >";
          InstallVallid = true;
          GetMayaPathVisible = true;
          CheckToolsPathsVisible = false;
          break;
        case InstallerState.Recap:
          break;
        default:
          break;
      }
    }
  }
}
