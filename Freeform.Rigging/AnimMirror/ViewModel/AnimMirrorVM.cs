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

namespace Freeform.Rigging.AnimMirror
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

    public class AnimMirrorVM : ViewModelBase
    {
        public event EventHandler MirrorCharacterHandler;

        public RelayCommand MirrorCharacterCommand { get; set; }
        public RelayCommand RemoveMirrorPairCommand { get; set; }
        public RelayCommand AddMirrorPairCommand { get; set; }


        ObservableCollection<MirrorPair> _mirrorPairList;
        public ObservableCollection<MirrorPair> MirrorPairList
        {
            get { return _mirrorPairList; }
            set
            {
                if (_mirrorPairList != value)
                {
                    _mirrorPairList = value;
                    RaisePropertyChanged("MirrorPairList");
                }
            }
        }


        bool _xAxis;
        public bool XAxis
        {
            get { return _xAxis; }
            set
            {
                if (_xAxis != value)
                {
                    _xAxis = value;
                    RaisePropertyChanged("XAxis");
                }
            }
        }

        bool _yAxis;
        public bool YAxis
        {
            get { return _yAxis; }
            set
            {
                if (_yAxis != value)
                {
                    _yAxis = value;
                    RaisePropertyChanged("YAxis");
                }
            }
        }

        bool _zAxis;
        public bool ZAxis
        {
            get { return _zAxis; }
            set
            {
                if (_zAxis != value)
                {
                    _zAxis = value;
                    RaisePropertyChanged("ZAxis");
                }
            }
        }

        bool _singleDirection;
        public bool SingleDirection
        {
            get { return _singleDirection; }
            set
            {
                if (_singleDirection != value)
                {
                    _singleDirection = value;
                    RaisePropertyChanged("SingleDirection");
                }
            }
        }
        
        bool _fullComponent;
        public bool FullComponent
        {
            get { return _fullComponent; }
            set
            {
                if (_fullComponent != value)
                {
                    _fullComponent = value;
                    RaisePropertyChanged("FullComponent");
                }
            }
        }

        bool _characterMirror;
        public bool CharacterMirror
        {
            get { return _characterMirror; }
            set
            {
                if (_characterMirror != value)
                {
                    _characterMirror = value;
                    RaisePropertyChanged("CharacterMirror");
                }
            }
        }

        bool _worldMirror;
        public bool WorldMirror
        {
            get { return _worldMirror; }
            set
            {
                if (_worldMirror != value)
                {
                    _worldMirror = value;
                    RaisePropertyChanged("WorldMirror");
                }
            }
        }
        
        bool _mirrorPose;
        public bool MirrorPose
        {
            get { return _mirrorPose; }
            set
            {
                if (_mirrorPose != value)
                {
                    _mirrorPose = value;
                    RaisePropertyChanged("MirrorPose");
                }
            }
        }

        bool _mirrorAnimation;
        public bool MirrorAnimation
        {
            get { return _mirrorAnimation; }
            set
            {
                if (_mirrorAnimation != value)
                {
                    _mirrorAnimation = value;
                    RaisePropertyChanged("MirrorAnimation");
                }
            }
        }


        public AnimMirrorVM()
        {
            XAxis = true;
            SingleDirection = false;
            FullComponent = false;
            CharacterMirror = true;
            MirrorPose = true;

            MirrorPairList = new ObservableCollection<MirrorPair>();

            MirrorCharacterCommand = new RelayCommand(MirrorCharacterCall);
            RemoveMirrorPairCommand = new RelayCommand(RemoveMirrorPairCall);
            AddMirrorPairCommand = new RelayCommand(AddMirrorPairCall);

            MirrorPairList.Add(new MirrorPair("left", "right"));
        }


        public void MirrorCharacterCall(object sender)
        {
            MirrorSettingsEventArgs eventArgs = new MirrorSettingsEventArgs()
            {
                MirrorPairList = MirrorPairList.ToList(),
                Axis = GetAxis(),
                WorldSpace = WorldMirror,
                SingleDirection = SingleDirection,
                MirrorComponent = FullComponent,
                MirrorPose = MirrorPose
            };
            MirrorCharacterHandler?.Invoke(this, eventArgs);
        }

        public void RemoveMirrorPairCall(object sender)
        {
            MirrorPair removePair = (MirrorPair)sender;
            MirrorPairList.Remove(removePair);
        }

        public void AddMirrorPairCall(object sender)
        {
            MirrorPairList.Add(new MirrorPair());
        }


        string GetAxis()
        {
            string axis = "x";
            if (XAxis == true) { axis = "x"; }
            else if (YAxis == true) { axis = "y"; }
            else if (ZAxis == true) { axis = "z"; }

            return axis;
        }


        public class MirrorSettingsEventArgs : EventArgs
        {
            public List<MirrorPair> MirrorPairList = null;
            public string Axis = "";
            public bool WorldSpace = false;
            public bool SingleDirection = false;
            public bool MirrorComponent = false;
            public bool MirrorPose = false;
        }
    }
}
