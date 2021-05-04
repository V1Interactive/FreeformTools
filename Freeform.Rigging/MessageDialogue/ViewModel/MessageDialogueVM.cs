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

namespace Freeform.Rigging.MessageDialogue
{
    using System;
    using System.Collections.Generic;
    using System.Collections.ObjectModel;
    using System.ComponentModel;
    using System.Linq;
    using System.Timers;
    using System.Windows.Controls;
    using System.Windows.Data;
    using System.Windows.Forms;
    using Freeform.Core.UI;

    public class MessageDialogueVM : ViewModelBase
    {
        public event EventHandler ConfirmHandler;
        public event EventHandler CancelHandler;

        public RelayCommand ConfirmCommand { get; set; }
        public RelayCommand CancelCommand { get; set; }


        string _windowTitle;
        public string WindowTitle
        {
            get { return _windowTitle; }
            set
            {
                _windowTitle = value;
                RaisePropertyChanged("WindowTitle");
            }
        }

        string _message;
        public string Message
        {
            get { return _message; }
            set
            {
                _message = value;
                RaisePropertyChanged("Message");
            }
        }

        bool _enableCancel;
        public bool EnableCancel
        {
            get { return _enableCancel; }
            set
            {
                _enableCancel = value;
                RaisePropertyChanged("EnableCancel");
            }
        }

        bool _dismissed;
        public bool Dismissed
        {
            get { return _dismissed; }
            set
            {
                _dismissed = value;
                RaisePropertyChanged("Dismissed");
            }
        }

        bool _confirmed;
        public bool Confirmed
        {
            get { return _confirmed; }
            set
            {
                _confirmed = value;
                RaisePropertyChanged("Confirmed");
            }
        }

        readonly System.Timers.Timer closeTimer;

        public MessageDialogueVM()
        {
            WindowTitle = "Message Dialogue";
            Confirmed = false;
            Dismissed = false;
            EnableCancel = false;

            ConfirmCommand = new RelayCommand(ConfirmCall);
            CancelCommand = new RelayCommand(CancelCall);

            closeTimer = new System.Timers.Timer(15000);
            closeTimer.Elapsed += AutoCloseEvent;
            closeTimer.Start();
        }

        public void ConfirmCall(object sender)
        {
            closeTimer.Stop();
            Confirmed = true;
            Dismissed = true;
            ConfirmHandler?.Invoke(this, null);
            Close();
        }

        private void AutoCloseEvent(object source, ElapsedEventArgs e)
        {
            DispatcherHelper.CheckBeginInvokeOnUI(
            () =>
            {
                // Dispatch back to the main thread
                CancelCall(null);
            });
        }

        public void CancelCall(object sender)
        {
            closeTimer.Stop();
            Confirmed = false;
            Dismissed = true;
            CancelHandler?.Invoke(this, null);
            Close();
        }
    }
}
