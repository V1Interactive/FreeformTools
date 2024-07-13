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

namespace Freeform.Rigging.RigBuilder
{
    using System;
    using System.Collections.Generic;
    using System.ComponentModel;
    using System.IO;
    using System.Linq;
    using System.Windows.Media.Imaging;
    using HelixResources.Style;
    using Freeform.Core.UI;
    using Freeform.Core.Helpers;
    using System.Collections.ObjectModel;
    using System.Windows.Data;

    public class RigItem : INotifyPropertyChanged
    {
        string _name;
        public string Name
        {
            get { return _name; }
            set
            {
                _name = value;
                RaisePropertyChanged("Name");
            }
        }

        public string ImagePath
        {
            get { return FilePath.Replace(".json", ".png"); }
        }

        string _filePath;
        public string FilePath
        {
            get { return _filePath; }
            set
            {
                _filePath = value;
                RaisePropertyChanged("FilePath");
                RaisePropertyChanged("ImagePath");
            }
        }

        // Style for selection highlighting in the main view
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

        // If the item is selected in the main view
        bool _isSelected;
        public bool IsSelected
        {
            get { return _isSelected; }
            set
            {
                if (_isSelected != value)
                {
                    _isSelected = value;
                    BorderStyle = value ? "SelectedBorder" : "V1Border";
                    RaisePropertyChanged("IsSelected");
                }
            }
        }


        public CollectionViewSource SideListViewSource { get; set; }
        ObservableCollection<RigItemBool> _sideList;
        public ObservableCollection<RigItemBool> SideList
        {
            get { return _sideList; }
            set
            {
                if (_sideList != value)
                {
                    _sideList = value;
                    RaisePropertyChanged("SideList");
                }
            }
        }

        public CollectionViewSource RegionListViewSource { get; set; }
        ObservableCollection<RigItemBool> _regionList;
        public ObservableCollection<RigItemBool> RegionList
        {
            get { return _regionList; }
            set
            {
                if (_regionList != value)
                {
                    _regionList = value;
                    RaisePropertyChanged("RegionList");
                }
            }
        }


        public RigItem(string name, string filePath)
        {
            Name = name;
            FilePath = filePath;

            BorderStyle = "V1Border";

            SideList = new ObservableCollection<RigItemBool>();
            SideListViewSource = new CollectionViewSource() { Source = SideList };
            SideListViewSource.SortDescriptions.Add(new SortDescription("Name", ListSortDirection.Ascending));

            RegionList = new ObservableCollection<RigItemBool>();
            RegionListViewSource = new CollectionViewSource() { Source = RegionList };
            RegionListViewSource.SortDescriptions.Add(new SortDescription("Name", ListSortDirection.Ascending));
        }

        public void AddSide(string name)
        {
            int index = SideList.ToList().FindIndex(f => f.GetName() == name);
            if(index == -1)
            {
                RigItemBool new_bool = new RigItemBool(name);
                SideList.Add(new_bool);
                RaisePropertyChanged("SideList");
            }
        }

        public void AddRegion(string name)
        {
            int index = RegionList.ToList().FindIndex(f => f.GetName() == name);
            if (index == -1)
            {
                RigItemBool new_bool = new RigItemBool(name);
                RegionList.Add(new_bool);
                RaisePropertyChanged("RegionList");
            }
        }


        // INotifyPropertyChanged definition for informing the UI of property changes
        protected void RaisePropertyChanged(string prop)
        {
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(prop));
        }
        public event PropertyChangedEventHandler PropertyChanged;
    }


    public class RigItemBool : INotifyPropertyChanged
    {
        string _name;
        public string Name
        {
            get { return _name.Replace("_", "__"); }
            set
            {
                _name = value;
                RaisePropertyChanged("Name");
            }
        }

        bool _isChecked;
        public bool IsChecked
        {
            get { return _isChecked; }
            set
            {
                _isChecked = value;
                RaisePropertyChanged("IsChecked");
            }
        }

        public RigItemBool(string name)
        {
            Name = name;
            IsChecked = true;
        }

        public string GetName()
        {
            return _name;
        }

        // INotifyPropertyChanged definition for informing the UI of property changes
        protected void RaisePropertyChanged(string prop)
        {
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(prop));
        }
        public event PropertyChangedEventHandler PropertyChanged;
    }
}
