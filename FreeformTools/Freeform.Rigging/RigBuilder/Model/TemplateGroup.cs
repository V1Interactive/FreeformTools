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
    using System.Windows.Data;
    using System.Collections.ObjectModel;



    public class TemplateGroup : INotifyPropertyChanged
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

        // Filter and sorting for the RigItemList
        public CollectionViewSource RigItemListViewSource { get; set; }
        ObservableCollection<RigItem> _rigItemList;
        public ObservableCollection<RigItem> RigItemList
        {
            get { return _rigItemList; }
            set
            {
                if (_rigItemList != value)
                {
                    _rigItemList = value;
                    RaisePropertyChanged("RigItemList");
                }
            }
        }

        RigItem _selectedItem;
        public RigItem SelectedItem
        {
            get { return _selectedItem; }
            set
            {
                if (_selectedItem != value)
                {
                    _selectedItem = value;
                    RaisePropertyChanged("SelectedItem");
                }
            }
        }

        public TemplateGroup(string name)
        {
            Name = name;

            RigItemList = new ObservableCollection<RigItem>();
            RigItemListViewSource = new CollectionViewSource { Source = RigItemList };
        }


        public RigItem AddItem(string name, string filePath)
        {
            RigItem newItem = new RigItem(name, filePath);
            RigItemList.Add(newItem);

            return newItem;
        }


        // INotifyPropertyChanged definition for informing the UI of property changes
        protected void RaisePropertyChanged(string prop)
        {
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(prop));
        }
        public event PropertyChangedEventHandler PropertyChanged;
    }
}
