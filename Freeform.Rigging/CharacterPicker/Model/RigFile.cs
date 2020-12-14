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

namespace Freeform.Rigging.CharacterPicker
{
    using System.ComponentModel;

    public class RigFile : INotifyPropertyChanged
    {
        string _fileName;
        public string FileName
        {
            get { return _fileName; }
            set
            {
                if (_fileName != value)
                {
                    _fileName = value;
                    RaisePropertyChanged("FileName");
                }
            }
        }

        string _fullPath;
        public string FullPath
        {
            get { return _fullPath; }
            set
            {
                if (_fullPath != value)
                {
                    _fullPath = value;
                    RaisePropertyChanged("FullPath");
                }
            }
        }

        string _gridStyle;
        public string GridStyle
        {
            get { return _gridStyle; }
            set
            {
                _gridStyle = value;
                RaisePropertyChanged("GridStyle");
            }
        }

        bool _isSelected;
        public bool IsSelected
        {
            get { return _isSelected; }
            set
            {
                if (_isSelected != value)
                {
                    _isSelected = value;
                    GridStyle = value ? "SelectedGrid" : "V1Grid";
                    RaisePropertyChanged("IsSelected");
                }
            }
        }


        public RigFile(string fileName, string fullPath)
        {
            GridStyle = "V1Grid";

            FileName = fileName;
            FullPath = fullPath;
        }


        void RaisePropertyChanged(string prop)
        {
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(prop));
        }
        public event PropertyChangedEventHandler PropertyChanged;
    }
}
