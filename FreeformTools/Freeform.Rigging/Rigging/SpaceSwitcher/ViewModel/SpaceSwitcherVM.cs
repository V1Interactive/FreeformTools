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

namespace Freeform.Rigging.SpaceSwitcher
{
    using System;
    using System.Collections.Generic;
    using System.Collections.ObjectModel;
    using System.ComponentModel;
    using System.Linq;
    using System.Windows.Controls;
    using System.Windows.Data;
    using System.Windows.Forms;
    using Freeform.Core.UI;

    public class SpaceSwitcherVM : ViewModelBase
    {
        public event EventHandler SetFrameHandler;
        public event EventHandler GetCurrentFrameHandler;
        public event EventHandler SwitchSpaceHandler;
        public event EventHandler SelectSwitchObjectsHandler;
        public event EventHandler SelectSwitchSpaceHandler;

        public RelayCommand SetFrameCommand { get; set; }
        public RelayCommand SetStartFrameCommand { get; set; }
        public RelayCommand SetEndFrameCommand { get; set; }
        public RelayCommand SwitchSpaceCommand { get; set; }
        public RelayCommand SelectSwitchObjectsCommand { get; set; }
        public RelayCommand SelectSwitchSpaceCommand { get; set; }


        private ObservableCollection<string> _availableSpaces;
        public ObservableCollection<string> AvailableSpaces
        {
            get { return _availableSpaces; }
            set
            {
                if (_availableSpaces != value)
                {
                    _availableSpaces = value;
                    RaisePropertyChanged("AvailableSpaces");
                }
            }
        }

        string _windowName;
        public string WindowName
        {
            get { return _windowName; }
            set
            {
                if (_windowName != value)
                {
                    _windowName = value;
                    RaisePropertyChanged("WindowName");
                }
            }
        }

        string _selectedSpace;
        public string SelectedSpace
        {
            get { return _selectedSpace; }
            set
            {
                if (_selectedSpace != value)
                {
                    _selectedSpace = value;
                    RaisePropertyChanged("SelectedSpace");
                }
            }
        }

        string _currentSpace;
        public string CurrentSpace
        {
            get { return _currentSpace; }
            set
            {
                if (_currentSpace != value)
                {
                    _currentSpace = value;
                    RaisePropertyChanged("CurrentSpace");
                }
            }
        }

        int _startFrame;
        public int StartFrame
        {
            get { return _startFrame; }
            set
            {
                if (_startFrame != value)
                {
                    _startFrame = value;
                    RaisePropertyChanged("StartFrame");
                }
            }
        }

        int _endFrame;
        public int EndFrame
        {
            get { return _endFrame; }
            set
            {
                if (_endFrame != value)
                {
                    _endFrame = value;
                    RaisePropertyChanged("EndFrame");
                }
            }
        }

        bool _keySwitch;
        public bool KeySwitch
        {
            get { return _keySwitch; }
            set
            {
                if (_keySwitch != value)
                {
                    _keySwitch = value;
                    RaisePropertyChanged("KeySwitch");
                }
            }
        }

        public SpaceSwitcherVM()
        {
            KeySwitch = true;

            AvailableSpaces = new ObservableCollection<string>();

            SetFrameCommand = new RelayCommand(SetFrameCall);
            SetStartFrameCommand = new RelayCommand(SetStartFrameCall);
            SetEndFrameCommand = new RelayCommand(SetEndFrameCall);

            SwitchSpaceCommand = new RelayCommand(SwitchSpaceCall);
            SelectSwitchObjectsCommand = new RelayCommand(SelectSwitchObjectsCall);
            SelectSwitchSpaceCommand = new RelayCommand(SelectSwitchSpaceCall);
        }

        public void SwitchSpaceCall(object sender)
        {
            if (SelectedSpace != null) {
                SwitchSpaceEventArgs eventArgs = new SwitchSpaceEventArgs()
                {
                    StartFrame = StartFrame,
                    EndFrame = EndFrame,
                    Space = int.Parse(SelectedSpace.Substring(SelectedSpace.Length - 1)),
                    KeySwitch = KeySwitch
                };
                SwitchSpaceHandler?.Invoke(this, eventArgs);
            }
            
        }

        public void SelectSwitchObjectsCall(object sender)
        {
            SelectSwitchObjectsHandler?.Invoke(this, null);
        }

        public void SelectSwitchSpaceCall(object sender)
        {
            if (SelectedSpace != null)
            {
                SwitchSpaceEventArgs eventArgs = new SwitchSpaceEventArgs()
                {
                    StartFrame = StartFrame,
                    EndFrame = EndFrame,
                    Space = int.Parse(SelectedSpace.Substring(SelectedSpace.Length - 1)),
                    KeySwitch = KeySwitch
                };
                SelectSwitchSpaceHandler?.Invoke(this, eventArgs);
            }
        }

        public void SetFrameCall(object sender)
        {
            SetFrameHandler?.Invoke(this, null);
        }

        public void SetStartFrameCall(object sender)
        {
            AttributeIntEventArgs eventArgs = new AttributeIntEventArgs();
            GetCurrentFrameHandler?.Invoke(this, eventArgs);

            StartFrame = eventArgs.Value;
        }

        public void SetEndFrameCall(object sender)
        {
            AttributeIntEventArgs eventArgs = new AttributeIntEventArgs();
            GetCurrentFrameHandler?.Invoke(this, eventArgs);

            EndFrame = eventArgs.Value;
        }


        public class AttributeIntEventArgs : EventArgs
        {
            public int Value = 0;
        }

        public class SwitchSpaceEventArgs : EventArgs
        {
            public int StartFrame = 0;
            public int EndFrame = 0;
            public int Space = 0;
            public bool KeySwitch = true;
        }
    }
}
