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
    using System.Collections;
    using System.Collections.Generic;
    using System.Collections.ObjectModel;
    using System.IO;
    using System.Linq;
    using System.Windows.Forms;
    using System.Windows.Media.Imaging;
    using Freeform.Core.Helpers;


    /*
    VM and wrapper object around a directory
    */
    public class UserDirectory : UserFile
    {
        // Name of the Directory
        public override string Name
        {
            get { return Path.GetFileName(ItemPath); }
        }

        // The directory this directory is in
        UserDirectory _parentDirectory;
        public UserDirectory ParentDirectory
        {
            get { return _parentDirectory; }
            set
            {
                if (_parentDirectory != value)
                {
                    _parentDirectory = value;
                    RaisePropertyChanged("ParentDirectory");
                }
            }
        }

        // All files in this directory
        ObservableCollection<UserFile> _files;
        public ObservableCollection<UserFile> Files
        {
            get { return _files; }
            set
            {
                if (_files != value)
                {
                    _files = value;
                    RaisePropertyChanged("Files");
                }
            }
        }

        // All immediate directories in this directory
        ObservableCollection<UserDirectory> _subfolders;
        public ObservableCollection<UserDirectory> Subfolders
        {
            get { return _subfolders; }
            set
            {
                if (_subfolders != value)
                {
                    _subfolders = value;
                    RaisePropertyChanged("Subfolders");
                }
            }
        }

        // All parent directories from this directory to the root
        public ObservableCollection<UserDirectory> DirectoryChain
        {
            get
            {
                List<UserDirectory> test = GetDirectoryChain();
                foreach (UserDirectory dir in test)
                {
                    dir.IsExpanded = true;
                }
                return new ObservableCollection<UserDirectory>(test);
            }
        }

        // Extra logic for if a directory is expanded
        public override bool IsExpanded
        {
            get => base.IsExpanded;
            set
            {
                if (_isExpanded != value)
                {
                    _isExpanded = value;

                    if (Control.ModifierKeys == Keys.Shift)
                    {
                        foreach (UserDirectory dir in Subfolders)
                        {
                            dir.IsExpanded = value;
                        }
                    }

                    RaisePropertyChanged("IsExpanded");
                }
            }
        }

        // All Files and Subfolders.  Concat demands a non-null argument
        public IEnumerable Items { get { return Subfolders?.Cast<UserFile>().Concat(Files); } }

        // Icon for a directory
        public override BitmapSource FileIcon
        {
            get
            {
                BitmapImage bitmap = new BitmapImage();
                Uri imageUri = new Uri("pack://application:,,,/HelixResources;component/Resources/folder.ico", UriKind.RelativeOrAbsolute);
                bitmap.BeginInit();
                bitmap.UriSource = imageUri;
                bitmap.EndInit();

                return bitmap;
            }
        }

        // Constructor
        public UserDirectory(string path) : base(path)
        {
            P4Status = P4Status.Null;
            FileStatus = FileWriteStatus.Null;

            Files = new ObservableCollection<UserFile>();
            Subfolders = new ObservableCollection<UserDirectory>();
        }

        // Updates the read/write status of the file
        public override void UpdateFileWriteStatus()
        {
            FileStatus = FileWriteStatus.Null;
        }

        // Updates the Perforce status of the file
        public override void UpdatePerforceStatus()
        {
            P4Status = P4Status.Null;

            ContentBrowserVM.UpdatePerforceStatus(Files.ToList());
        }

        // Update the folder with current subfolders
        public void UpdateSubFolderList()
        {
            string[] checkDirList = Directory.GetDirectories(ItemPath);
            foreach (string getPath in checkDirList)
            {
                if (!Subfolders.Select(x => x.ItemPath).Contains(getPath))
                {
                    UserDirectory newDir = new UserDirectory(getPath)
                    {
                        ParentDirectory = this ?? null
                    };

                    Subfolders.Add(newDir);
                }
            }

            List<UserDirectory> removeList = Subfolders.Where(p => checkDirList.All(p2 => p2 != p.ItemPath)).ToList();
            foreach (UserDirectory d in removeList)
            {
                Subfolders.Remove(d);
            }
        }

        // Update the folder with current files
        public void UpdateFileList(ref string UserMessage)
        {
            string[] checkFileList = Directory.GetFiles(ItemPath);

            foreach (string getPath in checkFileList)
            {
                try
                {
                    if (!Files.Select(x => x.ItemPath).Contains(getPath))
                    {
                        UserFile newFile = new UserFile(getPath);
                        Files.Add(newFile);
                        newFile.CheckFile(ref UserMessage);
                    }
                }
                catch (Exception) { UserMessage = getPath; }
            }

            List<UserFile> removeList = Files.Where(p => checkFileList.All(p2 => p2 != p.ItemPath)).ToList();
            foreach (UserFile f in removeList)
            {
                Files.Remove(f);
            }
        }


        // Gets all parent directories from this directory to the root
        public List<UserDirectory> GetDirectoryChain()
        {
            List<UserDirectory> returnList = new List<UserDirectory>();

            GetParentRecursive(this, returnList);
            returnList.Add(this);

            return returnList;
        }

        // Recursive - Gets all parent directories from this directory to the root
        public void GetParentRecursive(UserDirectory checkDir, List<UserDirectory> dirList)
        {
            if (checkDir.ParentDirectory != null)
            {
                GetParentRecursive(checkDir.ParentDirectory, dirList);
                dirList.Add(checkDir.ParentDirectory);
            }
        }

        // Recursive - Get all directories and files from this directory that match the filters
        public List<UserFile> GetFilteredFiles(string filterString)
        {
            string[] splitFilter = filterString.Split(null);
            List<UserFile> returnList = new List<UserFile>();

            foreach (UserFile file in Files.Concat(Subfolders))
            {
                if(filterString == "*" || splitFilter.All(x => file.Name.ToLower().Contains(x.ToLower())))
                {
                    returnList.Add(file);
                }
            }

            foreach (UserDirectory dir in Subfolders)
            {
                returnList.AddRange(dir.GetFilteredFiles(filterString));
            }

            return returnList;
        }

        // Recursive - Find a directory path in the tree of this directory
        public UserDirectory FindChildFolder(string searchFolder)
        {
            UserDirectory returnDir = null;
            foreach (UserDirectory folder in Subfolders)
            {
                if (returnDir != null) { break; }

                if (folder.ItemPath.ToLower() == searchFolder.ToLower()) { returnDir = folder; }
                else { returnDir = folder.FindChildFolder(searchFolder); }
            }

            return returnDir;
        }
    }
}
