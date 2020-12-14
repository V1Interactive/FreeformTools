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
    using System.Linq;
    using System.Text;
    using System.Threading.Tasks;
    using System.ComponentModel;

    public class MirrorPair : INotifyPropertyChanged
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

        string _mirrorSide;
        public string MirrorSide
        {
            get { return _mirrorSide; }
            set
            {
                if (_mirrorSide != value)
                {
                    _mirrorSide = value;
                    RaisePropertyChanged("MirrorSide");
                }
            }
        }


        public MirrorPair()
        {
        }

        public MirrorPair(string side, string mirrorSide) : this()
        {
            Side = side;
            MirrorSide = mirrorSide;
        }


        void RaisePropertyChanged(string prop)
        {
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(prop));
        }
        public event PropertyChangedEventHandler PropertyChanged;
    }
}
