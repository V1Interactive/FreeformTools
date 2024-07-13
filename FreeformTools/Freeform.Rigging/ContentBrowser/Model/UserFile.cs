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
    using Perforce.P4;
    using System;
    using System.Collections.Generic;
    using System.ComponentModel;
    using System.IO;
    using System.Linq;
    using System.Windows.Media.Imaging;
    using HelixResources.Style;
    using Freeform.Core.UI;
    using Freeform.Core.Helpers;
    using Freeform.Core.ConfigSettings;


    /*
    VM and wrapper object around a file
    */
    public class UserFile : INotifyPropertyChanged
    {
        public Exception FileError;

        // Object type name for sorting
        public string SortType
        {
            get
            {
                return GetType().ToString();
            }
        }

        // File path to this file or directory
        string _itemPath;
        public string ItemPath
        {
            get { return _itemPath; }
            set
            {
                if (_itemPath != value)
                {
                    _itemPath = value;
                    RaisePropertyChanged("ItemPath");
                    RaisePropertyChanged("FileIcon");
                    RaisePropertyChanged("Name");
                    RaisePropertyChanged("Folder");
                    RaisePropertyChanged("DateModified");
                }
            }
        }

        // File name without extension from ItemPath
        public virtual string ShortName
        {
            get { return Path.GetFileNameWithoutExtension(ItemPath); }
        }

        // File name with extension from ItemPath
        public virtual string Name
        {
            get { return Path.GetFileName(ItemPath); }
        }

        // Directory name from ItemPath
        public string Folder
        {
            get { return Path.GetDirectoryName(ItemPath); }
        }

        // Extension from ItemPath
        public string Extension
        {
            get { return Path.GetExtension(ItemPath).ToLower(); }
        }

        // Date the file was last modified
        public DateTime DateModified
        {
            get { return System.IO.File.GetLastWriteTime(ItemPath); }
        }

        // DateModified as a string
        public string DateModifiedString
        {
            get
            {
                DateTime date = DateModified;
                return date.ToShortDateString() + "   " + date.ToShortTimeString();
            }
        }

        // File Icon queried from shell
        public virtual BitmapSource FileIcon
        {
            get
            {
                BitmapSource icon = null;
                try
                {
                    if (System.IO.File.Exists(ItemPath))
                    {
                        icon = IconManager.GetLargeIcon(ItemPath, true, true);
                    }
                }
                catch(Exception e)
                {
                    FileError = e;
                }

                return icon;
            }
        }

        // The Perforce Status of the file
        P4Status _p4Status;
        public P4Status P4Status
        {
            get { return _p4Status; }
            set
            {
                if (_p4Status != value)
                {
                    _p4Status = value;
                    RaisePropertyChanged("P4Status");
                    RaisePropertyChanged("P4Icon");
                }
            }
        }
        // Icon from P4Status for easy binding
        public string P4Icon { get { return P4Status.Value; } }
        // Whether or not Perforce succeeded in checking this file
        public bool P4Success { get; set; }

        // Read/Write status of the file
        FileWriteStatus _fileStatus;
        public FileWriteStatus FileStatus
        {
            get { return _fileStatus; }
            set
            {
                if (_fileStatus != value)
                {
                    _fileStatus = value;
                    RaisePropertyChanged("FileStatus");
                    RaisePropertyChanged("FileStatusIcon");
                }
            }
        }
        // Icon for the file status
        public string FileStatusIcon { get { return FileStatus.Value; } }

        // Style for selection highlighting in the directory tree view
        string _borderStyle;
        public string BorderStyle
        {
            get { return _borderStyle; }
            set
            {
                _borderStyle = value;
                RaisePropertyChanged("BorderStyle");
            }
        }

        // If the directory is selected in the directory tree view
        bool _isSelected;
        public bool IsSelected
        {
            get { return _isSelected; }
            set
            {
                if (_isSelected != value)
                {
                    _isSelected = value;
                    IsExpanded = value ? value : IsExpanded;
                    BorderStyle = value ? "SelectedBorder" : "V1Border";
                    RaisePropertyChanged("IsSelected");
                }
            }
        }

        // Style for selection highlighting in the main file view
        string _viewBorderStyle;
        public string ViewBorderStyle
        {
            get { return _viewBorderStyle; }
            set
            {
                _viewBorderStyle = value;
                RaisePropertyChanged("ViewBorderStyle");
            }
        }

        // If the file is selected in the main file view
        bool _viewIsSelected;
        public bool ViewIsSelected
        {
            get { return _viewIsSelected; }
            set
            {
                if (_viewIsSelected != value)
                {
                    _viewIsSelected = value;
                    ViewBorderStyle = value ? "SelectedBorder" : "V1Border";
                    RaisePropertyChanged("ViewIsSelected");
                }
            }
        }

        // If the directory is expanded in the directory tree view
        protected bool _isExpanded;
        public virtual bool IsExpanded
        {
            get { return _isExpanded; }
            set
            {
                if (_isExpanded != value)
                {
                    _isExpanded = value;
                    RaisePropertyChanged("IsExpanded");
                }
            }
        }

        // Easy binding for if this is a UserFile or UserDirectory
        public bool IsFile
        {
            get { return typeof(UserFile) == this.GetType(); }
        }

        // Easy binding for if this is a .FBX File
        public bool IsFBX
        {
            get { return IsFile && Extension.ToLower() == ".fbx"; }
        }


    // Constructor
    public UserFile(string path)
        {
            P4Success = true;
            BorderStyle = "V1Border";
            ViewBorderStyle = "V1Border";
            ItemPath = path;
            FileError = null;

            UpdateFileWriteStatus();
            P4Status = P4Status.Unknown;
        }


        public void CheckFile(ref string UserMessage)
        {
            if (FileError != null)
            {
                UserMessage = string.Format("ERROR: {0} - {1}", Name, FileError.ToString());
                System.Windows.Clipboard.SetText(FileError.ToString());
            }
        }

        // Updates the Perforce and File read/write status of the file
        public void UpdateFileStatus()
        {
            UpdateFileWriteStatus();
            //UpdatePerforceStatus();
            if (FileIcon != null) { }
        }

        // Updates the read/write status of the file
        public virtual void UpdateFileWriteStatus()
        {
            try
            {
                FileInfo fileInfo = new FileInfo(ItemPath);
                if (fileInfo.IsReadOnly == true) { FileStatus = FileWriteStatus.Locked; }
                else { FileStatus = FileWriteStatus.Unlocked; }
            }
            catch(Exception e)
            {
                FileError = e;
            }
        }

        // Update the Perforce status of the file, and whether or not Perforce successfully checked the file
        public virtual void UpdatePerforceStatus()
        {
            ConfigManager configManager = new ConfigManager();
            PerforceConfig perforceConfig = (PerforceConfig)configManager.GetCategory(SettingsCategories.PERFORCE);
            if (perforceConfig.Enabled == false)
            {
                return;
            }

            // If Perforce is Down or errors on getting file status fail gracefully and set P4 status to unknown
            try
            {
                List<FileMetaData> p4Info = Perforce.FileStatus(ItemPath);
                if (p4Info == null) { P4Status = P4Status.Unknown; }
                else if (p4Info.FirstOrDefault().OtherUsers != null) { P4Status = P4Status.CheckedOutOther; }
                else if (p4Info.FirstOrDefault().Action == FileAction.None) { P4Status = P4Status.CheckedIn; }
                else if (p4Info.FirstOrDefault().Action == FileAction.Edit) { P4Status = P4Status.CheckedOut; }
                else if (p4Info.FirstOrDefault().Action == FileAction.Add) { P4Status = P4Status.Add; }
                else if (p4Info.FirstOrDefault().Action == FileAction.Delete) { P4Status = P4Status.Delete; }
                P4Success = true;
            }
            catch (Exception e)
            {
                P4Status = P4Status.Unknown;
                P4Success = false;
                FileError = e;
            }
        }


        // Perforce Checkout this file
        public void CheckoutCall(object sender)
        {
            Perforce.CheckoutFiles(new List<string>() { ItemPath });
            UpdateFileStatus();
        }

        // Perforce Add this file
        public void AddCall(object sender)
        {
            Perforce.AddFiles(new List<string>() { ItemPath });
            UpdateFileStatus();
        }

        // Perforce Delete this file
        public void DeleteCall(object sender)
        {
            Perforce.DeleteFiles(new List<string>() { ItemPath });
            UpdateFileStatus();
        }

        // Perforce Revert this file
        public void RevertCall(object sender)
        {
            Perforce.RevertFiles(new List<string>() { ItemPath });
            UpdateFileStatus();
        }


        // INotifyPropertyChanged definition for informing the UI of property changes
        protected void RaisePropertyChanged(string prop)
        {
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(prop));
        }
        public event PropertyChangedEventHandler PropertyChanged;
    }
}