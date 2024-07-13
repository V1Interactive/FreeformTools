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

using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace Freeform.Rigging.RegionEditor
{
    using System.ComponentModel;

    public class Region : INotifyPropertyChanged
    {
        string _side;
        public string Side
        {
            get { return _side; }
            set
            {
                if (_side != value)
                {
                    _side = value;
                    RaisePropertyChanged("Side");
                }
            }
        }

        string _name;
        public string Name
        {
            get { return _name; }
            set
            {
                if (_name != value)
                {
                    _name = value;
                    RaisePropertyChanged("Name");
                }
            }
        }

        string _group;
        public string Group
        {
            get { return _group; }
            set
            {
                if (_group != value)
                {
                    _group = value;
                    RaisePropertyChanged("Group");
                }
            }
        }

        string _root;
        public string Root
        {
            get { return _root; }
            set
            {
                if (_root != value)
                {
                    _root = value;
                    RaisePropertyChanged("Root");
                }
            }
        }

        string _end;
        public string End
        {
            get { return _end; }
            set
            {
                if (_end != value)
                {
                    _end = value;
                    RaisePropertyChanged("End");
                }
            }
        }

        float _comWeight;
        public float ComWeight
        {
            get { return _comWeight; }
            set
            {
                if (_comWeight != value)
                {
                    _comWeight = value;
                    RaisePropertyChanged("ComWeight");
                }
            }
        }

        string _comObject;
        public string ComObject
        {
            get { return _comObject; }
            set
            {
                if (_comObject != value)
                {
                    _comObject = value;
                    RaisePropertyChanged("ComObject");
                }
            }
        }

        string _comRegion;
        public string ComRegion
        {
            get { return _comRegion; }
            set
            {
                if (_comRegion != value)
                {
                    _comRegion = value;
                    RaisePropertyChanged("ComRegion");
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

        bool _isValid;
        public bool IsValid
        {
          get { return _isValid; }
          set
          {
            if (_isValid != value)
            {
              _isValid = value;
              Root = "Missing - Reload Region Editor";
              End = "Missing - Reload Region Editor";
              RaisePropertyChanged("IsValid");
            }
          }
        }

        public Region(string side, string name, string group, string root, string end, string comObject, string comRegion, float comWeight)
        {
            GridStyle = "V1Grid";

            Side = side;
            Name = name;
            Group = group;
            Root = root;
            End = end;
            ComObject = comObject;
            ComRegion = comRegion;
            ComWeight = comWeight;
        }


        void RaisePropertyChanged(string prop)
        {
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(prop));
        }
        public event PropertyChangedEventHandler PropertyChanged;
    }
}