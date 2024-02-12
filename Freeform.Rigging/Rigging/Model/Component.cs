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

    public class Component : INotifyPropertyChanged
    {
        public event EventHandler SelectComponentHandler;
        public event EventHandler TransferAnimHandler;
        public event EventHandler ToggleVisibilityComponentHandler;
        public event EventHandler AttributeChangedHandler;

        public RelayCommand TransferAnimCommand { get; set; }
        public RelayCommand ToggleVisibilityComponentCommand { get; set; }
        public RelayCommand ToggleSelectionLockCommand { get; set; }


        public string NodeName;
        public bool AddToSelection;
        public bool RunSelectionEvent;

        string _type;
        public string Type
        {
            get { return _type; }
            set
            {
                if (_type != value)
                {
                    _type = value;
                    RaisePropertyChanged("Type");
                }
            }
        }

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

        string _region;
        public string Region
        {
            get { return _region; }
            set
            {
                if (_region != value)
                {
                    _region = value;
                    RaisePropertyChanged("Region");
                }
            }
        }

        string _groupName;
        public string GroupName
        {
            get { return _groupName; }
            set
            {
                if (_groupName != value)
                {
                    _groupName = value;
                    RaisePropertyChanged("GroupName");
                }
            }
        }

        string _errorMessage;
        public string ErrorMessage
        {
            get { return _errorMessage; }
            set
            {
                _errorMessage = value;
                RaisePropertyChanged("ErrorMessage");
            }
        }

        bool _enabled;
        public bool Enabled
        {
            get { return _enabled; }
            set
            {
                if(_enabled != value)
                {
                    _enabled = value;
                    GridStyle = value ? "V1Grid" : "ErrorGrid";
                }
                RaisePropertyChanged("Enabled");
            }
        }

        bool _isVisible;
        public bool IsVisible
        {
            get { return _isVisible; }
            set
            {
                if(_isVisible != value)
                {
                    _isVisible = value;
                }

                SelectEventArgs eventArgs = new SelectEventArgs() { doAdd = value };
                ToggleVisibilityComponentHandler?.Invoke(this, eventArgs);

                if (_isVisible)
                    VisibleIcon = "pack://application:,,,/HelixResources;component/Resources/visibility-on.png";
                else
                    VisibleIcon = "pack://application:,,,/HelixResources;component/Resources/visibility-off.png";
            }
        }

        string _lockedState;
        public string LockedState
        {
            get { return _lockedState; }
            set
            {
                if (_lockedState != value)
                {
                    _lockedState = value;
                }

                SelectionLockIcon = string.Format("pack://application:,,,/HelixResources;component/Resources/{0}.ico", _lockedState);
                SelectionTooltip = string.Format("Selection Mode - {0}", _lockedState);

                AttributeStringEventArgs eventArgs = new AttributeStringEventArgs()
                {
                    NodeName = NodeName,
                    Attribute = "selection_lock",
                    Value = LockedState
                };
                AttributeChangedHandler?.Invoke(this, eventArgs);

                RaisePropertyChanged("LockedState");
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

        string _itemsControlStyle;
        public string ItemsControlStyle
        {
            get { return _itemsControlStyle; }
            set
            {
                _itemsControlStyle = value;
                RaisePropertyChanged("ItemsControlStyle");
            }
        }

        bool _isSelected;
        public bool IsSelected
        {
            get { return _isSelected; }
            set
            {
                _isSelected = value;

                string selectedStyle = Enabled ? "SelectedGrid" : "SelectedErrorGrid";
                string unSelectedStyle = Enabled ? "V1Grid" : "ErrorGrid";
                GridStyle = value ? selectedStyle : unSelectedStyle;
                ItemsControlStyle = value ? "SelectedItemsControl" : "ForegroundItemsControl";

                if (value == true && RunSelectionEvent) { SelectComponent(AddToSelection); }

                RaisePropertyChanged("IsSelected");
            }
        }

        string _visibleIcon;
        public string VisibleIcon
        {
            get { return _visibleIcon; }
            set
            {
                if(_visibleIcon != value)
                {
                    _visibleIcon = value;
                    RaisePropertyChanged("VisibleIcon");
                }
            }
        }

        string _selectionLockIcon;
        public string SelectionLockIcon
        {
            get { return _selectionLockIcon; }
            set
            {
                if (_selectionLockIcon != value)
                {
                    _selectionLockIcon = value;
                    RaisePropertyChanged("SelectionLockIcon");
                }
            }
        }

        string _selectionTooltip;
        public string SelectionTooltip
        {
            get { return _selectionTooltip; }
            set
            {
                if (_selectionTooltip != value)
                {
                    _selectionTooltip = value;
                    RaisePropertyChanged("SelectionTooltip");
                }
            }
        }


        public ObservableCollection<RigBarButton> _componentButtonList;
        public ObservableCollection<RigBarButton> ComponentButtonList
        {
            get { return _componentButtonList; }
            set
            {
                if (_componentButtonList != value)
                {
                    _componentButtonList = value;
                    RaisePropertyChanged("ComponentButtonList");
                }
            }
        }


        public Component(string metaNodeName, string aType, string aSide, string aRegion)
        {
            Enabled = true;
            NodeName = metaNodeName;
            Type = aType;
            Side = aSide;
            Region = aRegion;

            GridStyle = "V1Grid";
            ItemsControlStyle = "ForegroundItemsControl";
            IsVisible = true;
            LockedState = "unlocked";
            SelectionLockIcon = "pack://application:,,,/HelixResources;component/Resources/unlocked.ico";
            AddToSelection = false;
            RunSelectionEvent = true;

            ComponentButtonList = new ObservableCollection<RigBarButton>();

            TransferAnimCommand = new RelayCommand(TransferAnimEventCall);
            ToggleVisibilityComponentCommand = new RelayCommand(ToggleVisibilityEventCall);
            ToggleSelectionLockCommand = new RelayCommand(ToggleSelectionLockCall);
        }

        public void TransferAnimEventCall(object sender)
        {
            CharacterventArgs eventArgs = new CharacterventArgs()
            {
                character = (Character)sender
            };
            TransferAnimHandler?.Invoke(this, eventArgs);
        }

        public void ToggleVisibilityEventCall(object sender)
        {
            IsVisible = !IsVisible;
        }

        public void ToggleSelectionLockCall(object sender)
        {
            if(LockedState == "locked")
            {
                LockedState = "unlocked";
            }
            else if (LockedState == "unlocked")
            {
                LockedState = "locked";
            }
        }

        public void SelectComponent(bool forceAdd)
        {
            SelectEventArgs eventArgs = new SelectEventArgs();
            if (forceAdd == true || System.Windows.Forms.Control.ModifierKeys == Keys.Shift || System.Windows.Forms.Control.ModifierKeys == Keys.Control)
            {
                eventArgs.doAdd = true;
            }

            if (eventArgs.doAdd == false || (eventArgs.doAdd == true && Enabled == true))
                SelectComponentHandler?.Invoke(this, eventArgs);
        }


        #region EventArgs
        public class SelectEventArgs : EventArgs
        {
            public bool doAdd = false;
        }

        public class StringEventArgs : EventArgs
        {
            public string stringName = "";
        }

        public class CharacterventArgs : EventArgs
        {
            public Character character = null;
        }

        public class AttributeStringEventArgs : EventArgs
        {
            public string NodeName = "";
            public string Attribute = "";
            public string Type = "string";
            public string Value = "";
        }
        #endregion

        void RaisePropertyChanged(string prop)
        {
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(prop));
        }
        public event PropertyChangedEventHandler PropertyChanged;
    }
}
