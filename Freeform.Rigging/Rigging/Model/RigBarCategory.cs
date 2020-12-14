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

namespace Freeform.Rigging
{
    using System;
    using System.Collections.Generic;
    using System.Collections.ObjectModel;
    using System.ComponentModel;
    using System.Linq;
    using System.Text;
    using System.Threading.Tasks;



    public class RigBarCategory : INotifyPropertyChanged
    {
        bool _isVisible;
        public bool IsVisible
        {
            get { return _isVisible; }
            set
            {
                if (_isVisible != value)
                {
                    _isVisible = value;

                    foreach(RigBarButton button in RigButtonList)
                    {
                        button.IsVisible = _isVisible;
                    }

                    RaisePropertyChanged("IsVisible");
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

        string _imagePath;
        public string ImagePath
        {
            get { return _imagePath; }
            set
            {
                if (_imagePath != value)
                {
                    _imagePath = value;
                    RaisePropertyChanged("ImagePath");
                }
            }
        }

        public ObservableCollection<RigBarButton> _rigButtonList;
        public ObservableCollection<RigBarButton> RigButtonList
        {
            get { return _rigButtonList; }
            set
            {
                if (_rigButtonList != value)
                {
                    _rigButtonList = value;
                    RaisePropertyChanged("RigButtonList");
                }
            }
        }


        public RigBarCategory(string name)
        {
            _isVisible = true;
            _name = name;

            RigButtonList = new ObservableCollection<RigBarButton>();
        }


        public void AddButton(RigBarButton newButton)
        {
            RigButtonList.Add(newButton);
        }


        void RaisePropertyChanged(string prop)
        {
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(prop));
        }
        public event PropertyChangedEventHandler PropertyChanged;
    }
}
