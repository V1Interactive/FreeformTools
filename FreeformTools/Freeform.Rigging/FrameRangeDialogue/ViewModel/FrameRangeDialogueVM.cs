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

namespace Freeform.Rigging.FrameRangeDialogue
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

    public class FrameRangeDialogueVM : ViewModelBase
    {
        public event EventHandler SetFrameHandler;
        public event EventHandler GetCurrentFrameHandler;
        public event EventHandler CloseHandler;

        public RelayCommand SetFrameCommand { get; set; }
        public RelayCommand SetStartFrameCommand { get; set; }
        public RelayCommand SetEndFrameCommand { get; set; }

        public RelayCommand ConfirmCommand { get; set; }
        public RelayCommand CancelCommand { get; set; }


        int? _startFrame;
        public int? StartFrame
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

        int? _endFrame;
        public int? EndFrame
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


        public FrameRangeDialogueVM()
        {
            StartFrame = 0;
            EndFrame = 0;

            SetFrameCommand = new RelayCommand(SetFrameCall);
            SetStartFrameCommand = new RelayCommand(SetStartFrameCall);
            SetEndFrameCommand = new RelayCommand(SetEndFrameCall);

            ConfirmCommand = new RelayCommand(ConfirmCall);
            CancelCommand = new RelayCommand(CancelCall);
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

        public void ConfirmCall(object sender)
        {
            CloseHandler?.Invoke(this, null);
            Close();
        }

        public void CancelCall(object sender)
        {
            StartFrame = null;
            EndFrame = null;
            CloseHandler?.Invoke(this, null);
            Close();
        }


        public class AttributeIntEventArgs : EventArgs
        {
            public int Value = 0;
        }
    }
}
