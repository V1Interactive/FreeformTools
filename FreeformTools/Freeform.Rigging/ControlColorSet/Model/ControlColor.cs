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
    using System.ComponentModel;
    using System.Globalization;
    using System.Linq;
    using System.Text;
    using System.Threading.Tasks;
    using System.Windows.Media;

    public class ControlColor : INotifyPropertyChanged
    {
        public string SetName;

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

        public string MaterialName
        {
            get { return string.Format("rig_control_{0}_{1}_material", SetName, Name.ToLower()); }
        }

        public string ShadingGroup
        {
            get { return string.Format("rig_control_{0}_{1}_SG", SetName, Name.ToLower()); }
        }

        int _colorR;
        public int ColorR
        {
            get { return _colorR; }
            set
            {
                _colorR = value;
                SetHexString();
                RaisePropertyChanged("ColorR");
                RaisePropertyChanged("Color");
                RaisePropertyChanged("HexColor");
            }
        }

        int _colorG;
        public int ColorG
        {
            get { return _colorG; }
            set
            {
                _colorG = value;
                SetHexString();
                RaisePropertyChanged("ColorG");
                RaisePropertyChanged("Color");
                RaisePropertyChanged("HexColor");
            }
        }

        int _colorB;
        public int ColorB
        {
            get { return _colorB; }
            set
            {
                _colorB = value;
                SetHexString();
                RaisePropertyChanged("ColorB");
                RaisePropertyChanged("Color");
                RaisePropertyChanged("HexColor");
            }
        }

        int _alpha;
        public int Alpha
        {
            get { return _alpha; }
            set
            {
                _alpha = value;
                SetHexString();
                RaisePropertyChanged("Alpha");
                RaisePropertyChanged("Color");
                RaisePropertyChanged("HexColor");
            }
        }

        float _translucence;
        public float Translucence
        {
            get { return _translucence; }
            set
            {
                _translucence = value;
                RaisePropertyChanged("Translucence");
            }
        }

        string _hexColor;
        public string HexColor
        {
            get { return _hexColor; }
            set
            {
                string setValue = value.Replace("#", "");
                _hexColor = setValue;

                IEnumerable<string> splitValue = SplitHex(setValue);
                int i = 0;
                foreach(string hexValue in splitValue.Reverse())
                {
                    int intValue = int.Parse(hexValue, NumberStyles.HexNumber);
                    switch (i)
                    {
                        case 0:
                            ColorB = intValue;
                            break;
                        case 1:
                            ColorG = intValue;
                            break;
                        case 2:
                            ColorR = intValue;
                            break;
                        case 3:
                            Alpha = intValue;
                            break;
                    }
                    i++;
                }

                SetHexString();
                RaisePropertyChanged("HexColor");
            }
        }

        public SolidColorBrush Color
        {
            get
            {
                Color color = new Color
                {
                    R = Convert.ToByte(ColorR),
                    G = Convert.ToByte(ColorG),
                    B = Convert.ToByte(ColorB),
                    A = Convert.ToByte(Alpha)
                };
                return new SolidColorBrush(color);
            }
        }


        public ControlColor(string name)
        {
            Name = name;
            Alpha = 76;
            Translucence = 1;
        }


        void SetHexString()
        {
            string hexA = Alpha.ToString("X");
            string hexR = ColorR.ToString("X");
            string hexG = ColorG.ToString("X");
            string hexB = ColorB.ToString("X");

            // .ToString("X") returns "0" for a 0 value, we want full hex pairs, so replace with "00"
            if (hexA == "0") { hexA = "00"; }
            if (hexR == "0") { hexR = "00"; }
            if (hexG == "0") { hexG = "00"; }
            if (hexB == "0") { hexB = "00"; }

            _hexColor = hexA + hexR + hexG + hexB;
        }


        IEnumerable<string> SplitHex(string str)
        {
            int chunkSize = 2;
            return Enumerable.Range(0, str.Length / chunkSize)
                .Select(i => str.Substring(i * chunkSize, chunkSize));
        }

        void RaisePropertyChanged(string prop)
        {
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(prop));
        }
        public event PropertyChangedEventHandler PropertyChanged;
    }
}
