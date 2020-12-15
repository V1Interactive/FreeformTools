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
    using System.ComponentModel;
    using System.Collections.ObjectModel;
    using System.Linq;

    using Freeform.Core.UI;
    using Freeform.Core.Helpers;
    using System.Windows.Controls;
    using System.Windows.Media;
    using System.Windows.Forms;

    public class RigBarButton : INotifyPropertyChanged
    {
        public event EventHandler CommandHandler;
        public event EventHandler SaveSettingHandler;

        public RelayCommand ButtonCommand { get; set; }

        public string Data;

        bool _isEnabled;
        public bool IsEnabled
        {
            get { return _isEnabled; }
            set
            {
                if (_isEnabled != value)
                {
                    _isEnabled = value;
                    RaisePropertyChanged("IsEnabled");
                }
            }
        }

        bool _isVisible;
        public bool IsVisible
        {
            get { return _isVisible; }
            set
            {
                if (_isVisible != value)
                {
                    _isVisible = value;
                    RaisePropertyChanged("IsVisible");
                    SaveSettingHandler?.Invoke(this, new SaveBoolEventArgs() { name = Name + ".isVisible", value = _isVisible, category = "ToolVisibilitySettings" });
                }
            }
        }

        int _index;
        public int Index
        {
            get { return _index; }
            set
            {
                if (_index != value)
                {
                    _index = value;
                    RaisePropertyChanged("Index");
                }
            }
        }

        int _width;
        public int Width
        {
            get { return _width; }
            set
            {
                if (_width != value)
                {
                    _width = value;
                    RaisePropertyChanged("Width");
                }
            }
        }

        int _height;
        public int Height
        {
            get { return _height; }
            set
            {
                if (_height != value)
                {
                    _height = value;
                    RaisePropertyChanged("Height");
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

        string _statusImagePath;
        public string StatusImagePath
        {
            get { return _statusImagePath; }
            set
            {
                if (_statusImagePath != value)
                {
                    _statusImagePath = value;
                    RaisePropertyChanged("StatusImagePath");
                }
            }
        }
        
        string _secondaryStatusImagePath;
        public string SecondaryStatusImagePath
        {
            get { return _secondaryStatusImagePath; }
            set
            {
                if (_secondaryStatusImagePath != value)
                {
                    _secondaryStatusImagePath = value;
                    RaisePropertyChanged("SecondaryStatusImagePath");
                }
            }
        }

        string _tooltip;
        public string Tooltip
        {
            get { return _tooltip; }
            set
            {
                if (_tooltip != value)
                {
                    _tooltip = value;
                    RaisePropertyChanged("Tooltip");
                }
            }
        }

        public RigBarButton()
        {
            Width = 40;
            Height = 30;
            IsEnabled = true;
            IsVisible = true;
            ImagePath = "pack://application:,,,/HelixResources;component/Resources/refresh.ico";
            StatusImagePath = "";
            SecondaryStatusImagePath = "";
            Tooltip = "No Tooltip Available";
            ButtonCommand = new RelayCommand(ButtonCommandCall);
        }

        public virtual void ButtonCommandCall(object sender)
        {
            Character activeCharacter = (Character)sender;
            CharacterEventArgs eventArgs = new CharacterEventArgs() { Character = activeCharacter };

            if (System.Windows.Forms.Control.ModifierKeys == Keys.Shift)
            {
                eventArgs.Shift = true;
            }

            InvokeCommand(eventArgs);
        }

        public void InvokeCommand(EventArgs eventArgs)
        {
            CommandHandler?.Invoke(this, eventArgs);
        }

        #region EventArgs
        public class CharacterEventArgs : EventArgs
        {
            public Character Character = null;
            public bool Shift = false;
        }

        public class SaveBoolEventArgs : EventArgs
        {
            public string name = "";
            public bool value = false;
            public string category = "";
        }
        #endregion

        void RaisePropertyChanged(string prop)
        {
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(prop));
        }
        public event PropertyChangedEventHandler PropertyChanged;
    }


    public class SelectBarButton : RigBarButton
    {
        public string SelectionSet;

        public override void ButtonCommandCall(object sender)
        {
            RiggerVM riggerVM = (RiggerVM)sender;
            InvokeCommand(null);
        }
    }

    public class ComponentSelectButton : RigBarButton
    {
        // Used for distinguishing by type
    }
}
