/*
 * Freeform Rigging and Animation Tools
 * Copyright (C) 2020  Micah Zahm
 *
 * Freeform Rigging and Animation Tools is free software: you can redistribute it 
 * and/or modify it under the terms of the GNU General Public License as published 
 * by the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * Freeform Rigging and Animation Tools is distributed in the hope that it will 
 * be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with Freeform Rigging and Animation Tools.  
 * If not, see <https://www.gnu.org/licenses/>.
 */

namespace Freeform.Rigging.ContentBrowser
{
    using System;
    using System.Collections.Generic;
    using System.Collections.ObjectModel;
    using System.ComponentModel;
    using System.DirectoryServices.AccountManagement;
    using System.Diagnostics;
    using System.IO;
    using Freeform.Core.UI;
    using System.Windows.Data;
    using System.Linq;
    using Freeform.Core.Helpers;
    using Perforce.P4;
    using Freeform.Core.ConfigSettings;


    /*
    VM for the main Content Browser UI, handles all interaction between the UI and Data from Python and C#
    */
    class ContentBrowserVM : ViewModelBase
    {
        FileSystemWatcher DirectoryWatcher = new FileSystemWatcher()
        {
            NotifyFilter = NotifyFilters.DirectoryName |
                           NotifyFilters.FileName |
                           NotifyFilters.Attributes
        };

        public enum ViewState { FileView, DetailView };

        // UI Message strings
        readonly string DefaultMessage = string.Format("Enjoy the weather!", UserPrincipal.Current.DisplayName.Split()[0]);
        readonly string P4ErrorMessage = "Perforce has encountered an error, file status may not be accurate";

        // All Events for Python to register functionality on
        public event EventHandler OpenFileHandler;
        public event EventHandler ImportCombineHandler;

        // All Commands fired from UI controls
        public RelayCommand DoubleClickCommand { get; set; }
        public RelayCommand FilterFilesCommand { get; set; }
        public RelayCommand SetSelectedDirectoryCommand { get; set; }
        public RelayCommand HistoryBackCommand { get; set; }
        public RelayCommand HistoryForwardCommand { get; set; }
        public RelayCommand OpenFilterMenuCommand { get; set; }
        public RelayCommand CopyFilePathCommand { get; set; }
        public RelayCommand PasteFilePathCommand { get; set; }
        public RelayCommand OpenFileExplorerCommand { get; set; }
        public RelayCommand CheckoutCommand { get; set; }
        public RelayCommand AddCommand { get; set; }
        public RelayCommand DeleteCommand { get; set; }
        public RelayCommand RevertCommand { get; set; }
        public RelayCommand ChangeViewStateCommand { get; set; }
        public RelayCommand ImportCombineCommand { get; set; }

        // Main variable for determining the size of file Icons
    int _iconWidth;
        public int IconWidth
        {
            get { return _iconWidth; }
            set
            {
                if (_iconWidth != value)
                {
                    _iconWidth = value;
                    RaisePropertyChanged("IconWidth");
                    RaisePropertyChanged("IconHeight");
                    RaisePropertyChanged("ItemHeight");
                    RaisePropertyChanged("ItemWidth");
                    RaisePropertyChanged("ItemFontSize");
                }
            }
        }

        // Width of grid for file objects
        public int ItemWidth
        {
            get { return (int)(IconWidth * 1.3); }
        }

        // Height of file Icons
        public int IconHeight
        {
            get { return IconWidth; }
        }

        // Height of grid for file objects
        public int ItemHeight
        {
            get { return (int)(IconWidth * 1.3); }
        }

        // Size of font for files
        public int ItemFontSize
        {
            get { return IconWidth/8; }
        }

        // Title of the main UI window
        string _windowTitle;
        public string WindowTitle
        {
            get { return _windowTitle; }
            set
            {
                if (_windowTitle != value)
                {
                    _windowTitle = value;
                    RaisePropertyChanged("WindowTitle");
                }
            }
        }

        // Title of the main UI window
        string _launchProgram;
        public string LaunchProgram
        {
            get { return _launchProgram; }
            set
            {
                if (_launchProgram != value)
                {
                    _launchProgram = value;
                    RaisePropertyChanged("LaunchProgram");
                }
            }
        }

    // Message displayed to users for errors or other browser information
    string _userMessage;
        public string UserMessage
        {
            get { return _userMessage; }
            set
            {
                if (_userMessage != value)
                {
                    _userMessage = value;
                    RaisePropertyChanged("UserMessage");
                }
            }
        }

        string _fileViewIcon;
        public string FileViewIcon
        {
            get { return _fileViewIcon; }
            set
            {
                if (_fileViewIcon != value)
                {
                    _fileViewIcon = value;
                    RaisePropertyChanged("FileViewIcon");
                }
            }
        }

        bool _useDetailView;
        public bool UseDetailView
        {
            get { return _useDetailView; }
            set
            {
                _useDetailView = value;
                RaisePropertyChanged("UseDetailView");
            }
        }

        ViewState _uiViewState;
        public ViewState UIViewState
        {
            get { return _uiViewState; }
            set
            {
                _uiViewState = value;
                FileViewIcon = _uiViewState == ViewState.FileView ? "pack://application:,,,/HelixResources;component/Resources/vertical_bars.ico" : "pack://application:,,,/HelixResources;component/Resources/horizontal_bars.ico";
                UseDetailView = _uiViewState == ViewState.FileView ? false : true;
                RaisePropertyChanged("UIViewState");
            }
        }

        // Radio button bool for sorting the ContentList by name
        bool _contentNameSort;
        public bool ContentNameSort
        {
            get { return _contentNameSort; }
            set
            {
                if (_contentNameSort != value)
                {
                    if(value == true) { SortByName(); }
                    _contentNameSort = value;
                    RaisePropertyChanged("ContentNameSort");
                }
            }
        }

        // Radio button bool for sorting the ContentList by last modified date
        bool _contentDateSort;
        public bool ContentDateSort
        {
            get { return _contentDateSort; }
            set
            {
                if (_contentDateSort != value)
                {
                    if (value == true) { SortByDate(); }
                    _contentDateSort = value;
                    RaisePropertyChanged("ContentDateSort");
                }
            }
        }

        // Radio button bool for sorting the ContentList by extension
        bool _contentTypeSort;
        public bool ContentTypeSort
        {
            get { return _contentTypeSort; }
            set
            {
                if (_contentTypeSort != value)
                {
                    if (value == true) { SortByType(); }
                    _contentTypeSort = value;
                    RaisePropertyChanged("ContentTypeSort");
                }
            }
        }

        // Radio button bool for sorting the ContentList by extension
        bool _perforceStatusSort;
        public bool PerforceStatusSort
        {
            get { return _perforceStatusSort; }
            set
            {
                if (_perforceStatusSort != value)
                {
                    if (value == true) { SortByPerforce(); }
                    _perforceStatusSort = value;
                    RaisePropertyChanged("PerforceStatusSort");
                }
            }
        }

        // Bound to filter button click to open the context menu on left click
        bool _filterIsOpen;
        public bool FilterIsOpen
        {
            get { return _filterIsOpen; }
            set
            {
                if (_filterIsOpen != value)
                {
                    _filterIsOpen = value;
                    RaisePropertyChanged("FilterIsOpen");
                }
            }
        }

        // String to parse to handle searching the directory tree for matching file names
        string _fileFilter;
        public string FileFilter
        {
            get { return _fileFilter; }
            set
            {
                if (_fileFilter != value)
                {
                    _fileFilter = value;
                    // Update on empty here for immediate reaction to deleting the string
                    if (value == string.Empty) { UpdateContentList(); }
                    RaisePropertyChanged("FileFilter");
                }
            }
        }

        // Whether or not to display files
        bool _filterFiles;
        public bool FilterFiles
        {
            get { return _filterFiles; }
            set
            {
                if (_filterFiles != value)
                {
                    _filterFiles = value;
                    UpdateContentFilter();
                    RaisePropertyChanged("FilterFiles");
                }
            }
        }

        // Whether or not to display folders
        bool _filterFolders;
        public bool FilterFolders
        {
            get { return _filterFolders; }
            set
            {
                if (_filterFolders != value)
                {
                    _filterFolders = value;
                    UpdateContentFilter();
                    RaisePropertyChanged("FilterFolders");
                }
            }
        }

        // Whether or not to display Maya .ma files
        bool _filterMA;
        public bool FilterMA
        {
            get { return _filterMA; }
            set
            {
                if (_filterMA != value)
                {
                    FilterExtensionList.Remove(".ma");
                    if (value == true) { FilterExtensionList.Add(".ma"); }
                    _filterMA = value;
                    UpdateContentFilter();
                    RaisePropertyChanged("FilterMA");
                }
            }
        }

        // Whether or not to display 3dsMax .max files
        bool _filterMAX;
        public bool FilterMAX
        {
            get { return _filterMAX; }
            set
            {
                if (_filterMAX != value)
                {
                    FilterExtensionList.Remove(".max");
                    if (value == true) { FilterExtensionList.Add(".max"); }
                    _filterMAX = value;
                    UpdateContentFilter();
                    RaisePropertyChanged("FilterMAX");
                }
            }
        }

        // Whether or not to display FBX .fbx files
        bool _filterFBX;
        public bool FilterFBX
        {
            get { return _filterFBX; }
            set
            {
                if (_filterFBX != value)
                {
                    FilterExtensionList.Remove(".fbx");
                    if(value == true) { FilterExtensionList.Add(".fbx"); }
                    _filterFBX = value;
                    UpdateContentFilter();
                    RaisePropertyChanged("FilterFBX");
                }
            }
        }

        // Toggles all image file filters to it's value
        bool _filterAllImageFiles;
        public bool FilterAllImageFiles
        {
            get { return _filterAllImageFiles; }
            set
            {
                if (_filterAllImageFiles != value)
                {
                    _filterAllImageFiles = value;
                    FilterPSD = value;
                    FilterTGA = value;
                    FilterPNG = value;
                    FilterJPG = value;
                    RaisePropertyChanged("FilterAllImageFiles");
                    RaisePropertyChanged("FilterPSD");
                    RaisePropertyChanged("FilterTGA");
                    RaisePropertyChanged("FilterPNG");
                    RaisePropertyChanged("FilterJPG");
                }
            }
        }

        // Whether or not to display Photoshop .psd files
        bool _filterPSD;
        public bool FilterPSD
        {
            get { return _filterPSD; }
            set
            {
                if (_filterPSD != value)
                {
                    FilterExtensionList.Remove(".psd");
                    if (value == true) { FilterExtensionList.Add(".psd"); }
                    _filterPSD = value;
                    UpdateContentFilter();
                    RaisePropertyChanged("FilterPSD");
                }
            }
        }

        // Whether or not to display .tgs files
        bool _filterTGA;
        public bool FilterTGA
        {
            get { return _filterTGA; }
            set
            {
                if (_filterTGA != value)
                {
                    FilterExtensionList.Remove(".tga");
                    if (value == true) { FilterExtensionList.Add(".tga"); }
                    _filterTGA = value;
                    UpdateContentFilter();
                    RaisePropertyChanged("FilterTGA");
                }
            }
        }

        // Whether or not to display .png files
        bool _filterPNG;
        public bool FilterPNG
        {
            get { return _filterPNG; }
            set
            {
                if (_filterPNG != value)
                {
                    FilterExtensionList.Remove(".png");
                    if (value == true) { FilterExtensionList.Add(".png"); }
                    _filterPNG = value;
                    UpdateContentFilter();
                    RaisePropertyChanged("FilterPNG");
                }
            }
        }

        // Whether or not to display .jpg files
        bool _filterJPG;
        public bool FilterJPG
        {
            get { return _filterJPG; }
            set
            {
                if (_filterJPG != value)
                {
                    FilterExtensionList.Remove(".jpg");
                    if (value == true) { FilterExtensionList.Add(".jpg"); }
                    _filterJPG = value;
                    UpdateContentFilter();
                    RaisePropertyChanged("FilterJPG");
                }
            }
        }

        // List of all file extensions to filter by
        List<string> FilterExtensionList { get; set; }

        // History of directories navigated to
        List<UserDirectory> DirectoryHistory;
        // Whether or not to update the DirectoryHistory when directory is changed
        bool UpdateHistory;

        // Current position in the DirectoryHistory
        int _directoryHistoryIndex;
        public int DirectoryHistoryIndex
        {
            get { return _directoryHistoryIndex; }
            set
            {
                _directoryHistoryIndex = value;
                HistoryForwardEnabled = value == DirectoryHistory.Count - 1 ? false : true;
                HistoryBackEnabled = value == 0 ? false : true;
            }
        }

        // Toggles enabled status of the navigate history forward button
        bool _historyForwardEnabled;
        public bool HistoryForwardEnabled
        {
            get { return _historyForwardEnabled; }
            set
            {
                if (_historyForwardEnabled != value)
                {
                    _historyForwardEnabled = value;
                    RaisePropertyChanged("HistoryForwardEnabled");
                }
            }
        }

        // Toggles enabled status of the navigate history backward button
        bool _historyBackEnabled;
        public bool HistoryBackEnabled
        {
            get { return _historyBackEnabled; }
            set
            {
                if (_historyBackEnabled != value)
                {
                    _historyBackEnabled = value;
                    RaisePropertyChanged("HistoryBackEnabled");
                }
            }
        }

        // Toggles visibility of Perforce UI options
        bool _perforceEnabled;
        public bool PerforceEnabled
        {
            get { return _perforceEnabled; }
            set
            {
                if (_perforceEnabled != value)
                {
                    _perforceEnabled = value;
                    RaisePropertyChanged("PerforceEnabled");
                }
            }
        }

        // Whether or not Maya is the launch program
        public bool IsMaya
        {
            get { return LaunchProgram == "Maya"; }
        }

        // Selected directory in the directory tree
        UserDirectory _selectedDirectory;
        public UserDirectory SelectedDirectory
        {
            get { return _selectedDirectory; }
            set
            {
                if (_selectedDirectory != value)
                {
                    _selectedDirectory = value;
                    RaisePropertyChanged("SelectedDirectory");

                    if(UpdateHistory == true) { AddDirectoryToHistory(value); }

                    UpdateContentList();
                    Watch(value.ItemPath);
                }
            }
        }

        // First selected file or directory from the ContentList
        UserFile _selectedFile;
        public UserFile SelectedFile
        {
            get { return _selectedFile; }
            set
            {
                if (_selectedFile != value)
                {
                    _selectedFile = value;
                    RaisePropertyChanged("SelectedFile");
                }
            }
        }
        // List of all selected files in the ContentList
        public List<UserFile> SelectedFileList { get { return ContentList.Cast<UserFile>().Where(x => x.ViewIsSelected).ToList(); } }

        // Filter and sorting for the ContentList
        public CollectionViewSource ContentListViewSource { get; set; }
        // List of all files to display to the user in the main file view
        ObservableCollection<UserFile> _contentList;
        public ObservableCollection<UserFile> ContentList
        {
            get { return _contentList; }
            set
            {
                if (_contentList != value)
                {
                    _contentList = value;
                    RaisePropertyChanged("ContentList");
                }
            }
        }

        // List of all root directory objects that we build the directory tree from
        // Currently this only ever has 1 value, but is built to support multiple source directories
        ObservableCollection<UserFile> _rootDirectoryItems;
        public ObservableCollection<UserFile> RootDirectoryItems
        {
            get { return _rootDirectoryItems; }
            set
            {
                if (_rootDirectoryItems != value)
                {
                    _rootDirectoryItems = value;
                    RaisePropertyChanged("RootDirectoryItems");
                }
            }
        }

        // Constructor
        public ContentBrowserVM()
        {
            try
            {
                ConfigManager configManager = new ConfigManager();
                PerforceConfig perforceConfig = (PerforceConfig)configManager.GetCategory(SettingsCategories.PERFORCE);
                PerforceEnabled = perforceConfig.Enabled;

                FilterExtensionList = new List<string>();
                RootDirectoryItems = new ObservableCollection<UserFile>();
                ContentList = new ObservableCollection<UserFile>();

                DirectoryHistory = new List<UserDirectory>();
                DirectoryHistoryIndex = -1;
                UpdateHistory = true;

                ContentListViewSource = new CollectionViewSource { Source = ContentList };
                ContentNameSort = true;

                UserMessage = DefaultMessage;
                UIViewState = ViewState.FileView;
                IconWidth = 80;
                _fileFilter = string.Empty;
                _filterFiles = true;
                _filterFolders = true;

                DoubleClickCommand = new RelayCommand(DoubleClickCall);
                FilterFilesCommand = new RelayCommand(FilterFilesCall);
                SetSelectedDirectoryCommand = new RelayCommand(SetSelectedDirectoryCall);
                HistoryBackCommand = new RelayCommand(HistoryBackCall);
                HistoryForwardCommand = new RelayCommand(HistoryForwardCall);
                OpenFilterMenuCommand = new RelayCommand(OpenFilterMenuCall);
                CopyFilePathCommand = new RelayCommand(CopyFilePathCall);
                PasteFilePathCommand = new RelayCommand(PasteFilePathCall);
                OpenFileExplorerCommand = new RelayCommand(OpenFileExplorerCall);
                CheckoutCommand = new RelayCommand(CheckoutCall);
                AddCommand = new RelayCommand(AddCall);
                DeleteCommand = new RelayCommand(DeleteCall);
                RevertCommand = new RelayCommand(RevertCall);
                ChangeViewStateCommand = new RelayCommand(ChangeViewStateCall);
                ImportCombineCommand = new RelayCommand(ImportCombineCall);

                BuildDirectoryTree(configManager.GetContentRoot());
                BuildDirectoryTree(configManager.GetEngineContentRoot());

                DirectoryWatcher.Changed += new FileSystemEventHandler(UpdateTick);
                DirectoryWatcher.Renamed += new RenamedEventHandler(RenameTick);
                DirectoryWatcher.Deleted += new FileSystemEventHandler(UpdateTick);
                DirectoryWatcher.Created += new FileSystemEventHandler(UpdateTick);
                DirectoryWatcher.EnableRaisingEvents = true;
            }
            catch(Exception e)
            {
                UserMessage = string.Format("ERROR: {0}", e.ToString());
                System.Windows.Clipboard.SetText(e.ToString());
            }
        }

        // Updates the Perforce status of the file
        public static void UpdatePerforceStatus(List<UserFile> fileList)
        {
            ConfigManager configManager = new ConfigManager();
            PerforceConfig perforceConfig = (PerforceConfig)configManager.GetCategory(SettingsCategories.PERFORCE);
            if(perforceConfig.Enabled == false)
            {
                return;
            }

            string[] fileStatusList = fileList.Select(x => x.ItemPath).ToArray();

            if (fileStatusList.Any())
            {
                List<FileMetaData> p4Info = Perforce.FileStatus(fileStatusList);
                if(p4Info != null)
                {
                    foreach (FileMetaData metaData in p4Info)
                    {
                        UserFile updateFile = fileList.Where(x => x.ItemPath == metaData.LocalPath.Path).FirstOrDefault();
                        try
                        {
                            if (metaData == null) { updateFile.P4Status = P4Status.Unknown; }
                            else if (metaData.OtherUsers != null) { updateFile.P4Status = P4Status.CheckedOutOther; }
                            else if (metaData.Action == FileAction.None) { updateFile.P4Status = P4Status.CheckedIn; }
                            else if (metaData.Action == FileAction.Edit) { updateFile.P4Status = P4Status.CheckedOut; }
                            else if (metaData.Action == FileAction.Add) { updateFile.P4Status = P4Status.Add; }
                            else if (metaData.Action == FileAction.Delete) { updateFile.P4Status = P4Status.Delete; }
                            updateFile.P4Success = true;
                        }
                        catch (Exception e)
                        {
                            updateFile.P4Status = P4Status.Unknown;
                            updateFile.P4Success = false;
                            updateFile.FileError = e;
                            System.Windows.Clipboard.SetText(updateFile.FileError.ToString());
                        }
                    }
                }
            }
        }


        private void Watch(string watchPath)
        {
            DirectoryWatcher.Path = watchPath;
        }

        public void RenameTick(object sender, RenamedEventArgs e)
        {
            DispatcherHelper.CheckBeginInvokeOnUI(
            () =>
            {
                // Dispatch back to the main thread
                UpdateContentList();
            });
        }

        public void UpdateTick(object sender, FileSystemEventArgs e)
        {
            DispatcherHelper.CheckBeginInvokeOnUI(
            () =>
            {
                // Dispatch back to the main thread
                UpdateContentList();
            });
        }

        // Clear ContentListViewSource and sort it by Name
        public void SortByName()
        {
            ContentListViewSource.SortDescriptions.Clear();
            ContentListViewSource.SortDescriptions.Add(new SortDescription("SortType", ListSortDirection.Ascending));
            ContentListViewSource.SortDescriptions.Add(new SortDescription("Name", ListSortDirection.Ascending));
        }

        // Clear ContentListViewSource and sort it by DateModified
        public void SortByDate()
        {
            ContentListViewSource.SortDescriptions.Clear();
            ContentListViewSource.SortDescriptions.Add(new SortDescription("SortType", ListSortDirection.Ascending));
            ContentListViewSource.SortDescriptions.Add(new SortDescription("DateModified", ListSortDirection.Descending));
        }

        // Clear ContentListViewSource and sort it by Extension
        public void SortByType()
        {
            ContentListViewSource.SortDescriptions.Clear();
            ContentListViewSource.SortDescriptions.Add(new SortDescription("SortType", ListSortDirection.Ascending));
            ContentListViewSource.SortDescriptions.Add(new SortDescription("Extension", ListSortDirection.Descending));
        }

        public void SortByPerforce()
        {
            ContentListViewSource.SortDescriptions.Clear();
            ContentListViewSource.SortDescriptions.Add(new SortDescription("SortType", ListSortDirection.Ascending));
            ContentListViewSource.SortDescriptions.Add(new SortDescription("P4Status", ListSortDirection.Ascending));
            ContentListViewSource.SortDescriptions.Add(new SortDescription("Name", ListSortDirection.Ascending));
        }

        // Selected the directory tree item with a matching ItemPath passed in path string
        // Used to handle pasting a file path into the content browser to navitage to the pasted path
        public void NavigateToPath(string path)
        {
            string filePath = string.Empty;

            // If path is a file get the Directory of the file instead
            if (Path.HasExtension(path))
            {
                filePath = path;
                string extension = Path.GetExtension(path);
                path = Path.GetDirectoryName(path);

                if (extension == ".uasset")
                {
                    path = path.Replace("Robogore\\Content", "Data");
                    path = FindDirectory(path);
                }
            }

            if (System.IO.File.Exists(path) || Directory.Exists(path))
            {
                UserDirectory foundDirectory = null;

                foreach (UserFile rootDirectory in RootDirectoryItems)
                {
                    if (path.ToLower().Contains(rootDirectory.ItemPath.ToLower()))
                    {
                        foundDirectory = (rootDirectory as UserDirectory).FindChildFolder(path);
                    }
                }

                if (foundDirectory != null)
                {
                    SelectedDirectory = foundDirectory;
                    foundDirectory.IsSelected = true;
                }
            }
            
            if (filePath != string.Empty)
            {
                foreach (UserFile file in SelectedDirectory.Files)
                {
                    if (file.ShortName == Path.GetFileNameWithoutExtension(filePath))
                    {
                        file.ViewIsSelected = true;
                        SelectedFile = file;
                    }
                }
            }
        }

        // If the Directory doesn't exist keep checking parent directories until we find one that does exist
        public string FindDirectory(string path)
        {
            int count = 0;
            while((Directory.Exists(path) != true && path != null) || count > 10)
            {
                path = Path.GetDirectoryName(path);
                count += 1;
            }

            return path;
        }

        // Build out the tree of directories from a root path
        public void BuildDirectoryTree(string path)
        {
            if (Directory.Exists(path))
            {
                UserDirectory rootDirectory = CreateDirectory(path, null);
                RootDirectoryItems.Add(rootDirectory);
                SelectedDirectory = rootDirectory;
                SelectedDirectory.IsExpanded = true;
                SelectedDirectory.IsSelected = true;
            }
        }

        public void CheckFile(UserFile file)
        {
            if (file.FileError != null)
            {
                UserMessage = string.Format("ERROR: {0} - {1}", file.Name, file.FileError.ToString());
                System.Windows.Clipboard.SetText(file.FileError.ToString());
            }
        }

        // Recursive, create the directory at passed in path and all sub directories within
        public UserDirectory CreateDirectory(string path, UserDirectory parent)
        {
            UserDirectory returnDir = new UserDirectory(path)
            {
                ParentDirectory = parent ?? null
            };

            returnDir.UpdateFileList(ref _userMessage);
            RaisePropertyChanged("UserMessage");

            foreach (string getPath in Directory.GetDirectories(path))
            {
                returnDir.Subfolders.Add(CreateDirectory(getPath, returnDir));
            }

            return returnDir;
        }

        // Update the ContentList list of files with all files and directories in the currently selected directory
        public void UpdateContentList()
        {
            if (SelectedDirectory != null)
            {
                FileFilter = string.Empty;
                ContentList.Clear();

                SelectedDirectory.UpdateFileList(ref _userMessage);
                SelectedDirectory.UpdateSubFolderList();

                foreach (UserDirectory folder in SelectedDirectory.Subfolders)
                {
                    ContentList.Add(folder);
                }

                foreach (UserFile file in SelectedDirectory.Files)
                {
                    //file.UpdateFileStatus();
                    ContentList.Add(file);
                    file.CheckFile(ref _userMessage);
                }

                SelectedDirectory.UpdatePerforceStatus();
                RaisePropertyChanged("UserMessage");
            }

            if (ContentList != null) { UserMessage = ContentList.Any(x => x.P4Success == false) ? P4ErrorMessage : UserMessage; }
        }

        // Adds a UserDirectory object into the DirectoryHistory list, if the DirectoryHistoryIndex is in the middle of the
        // list remove all items after the index before adding the new directory
        public void AddDirectoryToHistory(UserDirectory dir)
        {
            if (DirectoryHistoryIndex != -1 && DirectoryHistoryIndex != DirectoryHistory.Count - 1)
            {
                DirectoryHistory.RemoveRange(DirectoryHistoryIndex + 1, DirectoryHistory.Count - (DirectoryHistoryIndex + 1));
            }

            DirectoryHistory.Add(dir);
            DirectoryHistoryIndex = DirectoryHistory.Count - 1;
        }

        // Searches all files and directories in the directory tree starting at the selected directory for any that match
        // the FileFilter string
        public void GetFilteredFilesFromSelected()
        {
            ContentList.Clear();

            List<UserFile> FilteredFileList = SelectedDirectory.GetFilteredFiles(FileFilter);

            UpdatePerforceStatus(FilteredFileList);
            foreach (UserFile file in SelectedDirectory.GetFilteredFiles(FileFilter))
            {
                file.UpdateFileStatus();
                ContentList.Add(file);
                file.CheckFile(ref _userMessage);
                RaisePropertyChanged("UserMessage");
            }

            if (ContentList != null) { UserMessage = ContentList.Any(x => x.P4Success == false) ? P4ErrorMessage : UserMessage; }
        }

        // Run the filter on ContentListViewSource
        void UpdateContentFilter()
        {
            AddContentFilter();

            ContentListViewSource.View.Refresh();

            if (!ContentListViewSource.View.IsEmpty)
            {
                var enumerator = ContentListViewSource.View.GetEnumerator();
                enumerator.MoveNext();
            }
        }

        // Helper to run the filter method on ContentListViewSource
        void AddContentFilter()
        {
            ContentListViewSource.Filter -= new FilterEventHandler(ContentFilter);
            ContentListViewSource.Filter += new FilterEventHandler(ContentFilter);
        }

        // Logic to filter the ContentListViewSource based extensions in the FilterExtensionList
        void ContentFilter(object sender, FilterEventArgs e)
        {
            e.Accepted = false;

            if (e.Item is UserFile src)
            {
                // Filter folders
                if (src.IsFile == false && FilterFolders == true)
                {
                    e.Accepted = true;
                }
                // Filter files
                else if (src.IsFile == true && FilterFiles == true)
                {
                    if (FilterExtensionList.Contains(src.Extension) || FilterExtensionList.Count == 0)
                    {
                        e.Accepted = true;
                    }
                }
            }
        }


        // Navigate into a directory, or open a file either with the attached program or the default program for it
        public void DoubleClickCall(object sender)
        {
            if(sender.GetType() == typeof(UserDirectory))
            {
                UserDirectory clickedDirectory = (UserDirectory)sender;
                SelectedDirectory.IsExpanded = true;
                clickedDirectory.ViewIsSelected = false;
                clickedDirectory.IsSelected = true;
                clickedDirectory.IsExpanded = true;
                SelectedDirectory = clickedDirectory;
            }
            else if (sender.GetType() == typeof(UserFile))
            {
                UserFile clickedFile = (UserFile)sender;
                if(OpenFileHandler != null)
                {
                    OpenFileEventArgs eventArgs = new OpenFileEventArgs
                    {
                        FilePath = clickedFile.ItemPath
                    };
                    OpenFileHandler?.Invoke(this, eventArgs);
                }
                else
                {
                    Process.Start(clickedFile.ItemPath);
                }
            }
        }

        // Runs the ContentList filters from UI command
        public void FilterFilesCall(object sender)
        {
            if(FileFilter != string.Empty) { GetFilteredFilesFromSelected(); }
            UpdateContentFilter();
        }

        // Sets the selected Directory from UI command
        public void SetSelectedDirectoryCall(object sender)
        {
            UserDirectory clickedDirectory = (UserDirectory)sender;
            clickedDirectory.IsSelected = true;
            SelectedDirectory = (UserDirectory)sender;
        }

        // Navigate back 1 index in the DirectoryHistory
        public void HistoryBackCall(object sender)
        {
            if(DirectoryHistoryIndex != 0) { DirectoryHistoryIndex -= 1; }
            UpdateHistory = false;
            SelectedDirectory = DirectoryHistory[DirectoryHistoryIndex];
            SelectedDirectory.IsSelected = true;
            UpdateHistory = true;
        }

        // Navigate forward 1 index in the DirectoryHistory
        public void HistoryForwardCall(object sender)
        {
            if (DirectoryHistoryIndex != DirectoryHistory.Count-1) { DirectoryHistoryIndex += 1; }
            UpdateHistory = false;
            SelectedDirectory = DirectoryHistory[DirectoryHistoryIndex];
            SelectedDirectory.IsSelected = true;
            UpdateHistory = true;
        }

        // UI Command to open the file filter context menu
        public void OpenFilterMenuCall(object sender)
        {
            FilterIsOpen = true;
        }

        // UI Command to copy the file path from the SelectedFile to the windows clipboard
        public void CopyFilePathCall(object sender)
        {
            string clipPath = string.Empty;
            foreach (UserFile file in SelectedFileList)
                clipPath += file.ItemPath + "\n";

            // If clipPath is popualted by SelectedFileList remove the last new line, if not grab it from the SelectedFile or Directory
            if (clipPath != string.Empty)
                clipPath = clipPath.TrimEnd('\n');
            else
                clipPath = SelectedFile != null ? SelectedFile.ItemPath : SelectedDirectory.ItemPath;

            // Only copy text if we have a path
            if (clipPath != string.Empty)
                System.Windows.Clipboard.SetText(clipPath);
        }

        // UI Command to handle pulling text from the windows clipboard and if it's a directory path, navigate to it
        public void PasteFilePathCall(object sender)
        {
            string directoryPath = System.Windows.Clipboard.GetText();
            directoryPath = directoryPath.Trim('\"');
            NavigateToPath(directoryPath);
        }

        // UI Command to open the directory of file path in windows explorer
        public void OpenFileExplorerCall(object sender)
        {   
            if (sender == null)
            {
                sender = SelectedDirectory != null ? SelectedDirectory : SelectedFile;
            }

            if (sender != null)
            {
                UserFile openFile = (UserFile)sender;
                string navPath = openFile.GetType() == typeof(UserFile) ? openFile.Folder : openFile.ItemPath;
                Process.Start("explorer.exe", navPath);
            }
        }

        // Perforce Checkout all selected files
        public void CheckoutCall(object sender)
        {
            foreach(UserFile file in SelectedFileList)
            {
                if (file.IsFile)
                {
                    file.CheckoutCall(sender);
                }
            }
        }

        // Perforce Add all selected files
        public void AddCall(object sender)
        {
            foreach (UserFile file in SelectedFileList)
            {
                if (file.IsFile)
                {
                    file.AddCall(sender);
                }
            }
        }

        // Perforce Delete all selected files
        public void DeleteCall(object sender)
        {
            foreach (UserFile file in SelectedFileList)
            {
                if (file.IsFile)
                {
                    file.DeleteCall(sender);
                }
            }
        }

        // Perforce Revert all selected files
        public void RevertCall(object sender)
        {
            foreach (UserFile file in SelectedFileList)
            {
                if (file.IsFile)
                {
                    file.RevertCall(sender);
                }
            }
        }

        public void ChangeViewStateCall(object sender)
        {
            if (UIViewState == ViewState.FileView)
                UIViewState = ViewState.DetailView;
            else if(UIViewState == ViewState.DetailView)
                UIViewState = ViewState.FileView;
        }

        public void ImportCombineCall(object sender)
        {
            ImportCombineEventArgs eventArgs = new ImportCombineEventArgs
            {
                FilePathList = SelectedFileList
            };
            ImportCombineHandler?.Invoke(this, eventArgs);
        }


        // EventArgs to pass a file path to Python
        class OpenFileEventArgs : EventArgs
        {
            public string FilePath = string.Empty;
        }
        // EventArgs to pass a file path to Python
        public class ImportCombineEventArgs : EventArgs
        {
          public List<UserFile> FilePathList = new List<UserFile>();
        }
  }
}
