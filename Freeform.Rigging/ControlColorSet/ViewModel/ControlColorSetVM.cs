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

namespace Freeform.Rigging.ControlColorSet
{
    using System;
    using System.Collections.Generic;
    using System.Collections.ObjectModel;
    using System.ComponentModel;
    using System.Globalization;
    using System.Linq;
    using System.Windows.Controls;
    using System.Windows.Data;
    using System.Windows.Forms;
    using System.Windows.Input;
    using Freeform.Core.UI;

    public class ControlColorSetVM : ViewModelBase
    {
        public event EventHandler SaveColorsHandler;
        public event EventHandler ApplySelectedHandler;
        public event EventHandler PickMaterialHandler;
        public event EventHandler SaveSettingHandler;

        public RelayCommand SaveColorsCommand { get; set; }
        public RelayCommand AddColorCommand { get; set; }
        public RelayCommand AddColorSetCommand { get; set; }
        public RelayCommand RemoveColorCommand { get; set; }
        public RelayCommand RemoveColorSetCommand { get; set; }
        public RelayCommand ApplySelectedColorCommand { get; set; }
        public RelayCommand PickMaterialCommand { get; set; }


        bool _useColorSet;
        public bool UseColorSet
        {
            get { return _useColorSet; }
            set
            {
                _useColorSet = value;
                RaisePropertyChanged("UseColorSet");
                SaveSettingHandler?.Invoke(this, new SaveBoolEventArgs() { name = "use_color_set", value = _useColorSet, category = "Rig_Materials" });
            }
        }

        ObservableCollection<ColorSet> _colorSetList;
        public ObservableCollection<ColorSet> ColorSetList
        {
            get { return _colorSetList; }
            set
            {
                if (_colorSetList != value)
                {
                    _colorSetList = value;
                    RaisePropertyChanged("ColorList");
                }
            }
        }
        public CollectionViewSource ColorSetListViewSource { get; set; }

        public ColorSet DefaultColorSet;
        ColorSet _selectedColorSet;
        public ColorSet SelectedColorSet
        {
            get { return _selectedColorSet; }
            set
            {
                if (_selectedColorSet != value)
                {
                    _selectedColorSet = value;
                    RaisePropertyChanged("SelectedColorSet");
                }
            }
        }

        int _selectedIndex;
        public int SelectedIndex
        {
            get { return _selectedIndex; }
            set
            {
                if (_selectedIndex != value)
                {
                    _selectedIndex = value;
                    RaisePropertyChanged("SelectedIndex");
                }
            }
        }

        string _newSetName;
        public string NewSetName
        {
            get { return _newSetName; }
            set
            {
                _newSetName = value;
                RaisePropertyChanged("NewSetName");
            }
        }


        public ControlColorSetVM()
        {
            NewSetName = "new_set";
            DefaultColorSet = new ColorSet("default")
            {
                Index = 0
            };

            ColorSetList = new ObservableCollection<ColorSet>
            {
                DefaultColorSet
            };

            ColorSetListViewSource = new CollectionViewSource
            {
                Source = ColorSetList
            };
            ColorSetListViewSource.SortDescriptions.Add(new SortDescription("Index", ListSortDirection.Ascending));
            ColorSetListViewSource.SortDescriptions.Add(new SortDescription("Name", ListSortDirection.Ascending));

            SaveColorsCommand = new RelayCommand(SaveColorsCall);
            AddColorCommand = new RelayCommand(AddColorCall);
            AddColorSetCommand = new RelayCommand(AddColorSetCall);
            RemoveColorCommand = new RelayCommand(RemoveColorCall);
            RemoveColorSetCommand = new RelayCommand(RemoveColorSetCall);
            ApplySelectedColorCommand = new RelayCommand(ApplySelectedColorCall);
            PickMaterialCommand = new RelayCommand(PickMaterialCall);
        }


        public void AddColorSet(ColorSet colorSet)
        {
            ColorSetList.Add(colorSet);
        }


        public void SaveColorsCall(object sender)
        {
            SaveColorSetsEventArgs eventArgs = new SaveColorSetsEventArgs()
            {
                ColorSetList = ColorSetList.ToList()
            };
            SaveColorsHandler?.Invoke(this, eventArgs);
        }

        public void AddColorCall(object sender)
        {
            SelectedColorSet.ColorList.Add(new ControlColor("_new_side"));
        }

        public void AddColorSetCall(object Sender)
        {
            if(NewSetName != string.Empty)
                ColorSetList.Add(new ColorSet(NewSetName));
        }

        public void RemoveColorCall(object sender)
        {
            ControlColor removeColor = (ControlColor)sender;
            SelectedColorSet.ColorList.Remove(removeColor);
        }

        public void RemoveColorSetCall(object sender)
        {
            ColorSet removeSet = (ColorSet)sender;
            if(removeSet != DefaultColorSet)
                ColorSetList.Remove(removeSet);
        }

        public void ApplySelectedColorCall(object sender)
        {
            ControlColor applyColor = (ControlColor)sender;

            ColorEventArgs eventArgs = new ColorEventArgs { Color = applyColor };
            ApplySelectedHandler?.Invoke(this, eventArgs);
        }

        public void PickMaterialCall(object sender)
        {
            ControlColor pickColor = (ControlColor)sender;

            ColorEventArgs eventArgs = new ColorEventArgs { Color = pickColor };
            PickMaterialHandler?.Invoke(this, eventArgs);
        }


        public class SaveColorSetsEventArgs : EventArgs
        {
            public List<ColorSet> ColorSetList = null;
        }

        public class ColorEventArgs : EventArgs
        {
            public ControlColor Color = null;
        }

        public class SaveBoolEventArgs : EventArgs
        {
            public string name = "";
            public bool value = false;
            public string category = "";
        }
    }
}
