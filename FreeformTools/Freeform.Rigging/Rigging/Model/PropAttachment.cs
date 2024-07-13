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
    using System.Windows.Data;
    using Freeform.Core.UI;
    using System.Windows.Forms;
    using System.IO;


    public class PropFile : INotifyPropertyChanged
    {
        string _filePath;
        public string FilePath
        {
            get { return _filePath; }
            set
            {
                if (_filePath != value)
                {
                    _filePath = value;
                    RaisePropertyChanged("FilePath");
                    RaisePropertyChanged("FileName");
                }
            }
        }
        public string FileName
        {
            get { return Path.GetFileNameWithoutExtension(FilePath); }
        }


        public PropFile(string filePath)
        {
            FilePath = filePath;
        }


        void RaisePropertyChanged(string prop)
        {
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(prop));
        }
        public event PropertyChangedEventHandler PropertyChanged;
    }


    public class PropAttachment : INotifyPropertyChanged
    {
        readonly PropFile NullProp = new PropFile("Empty");

        public event EventHandler AttributeChangedHandler;
        public event EventHandler AddAttachmentHandler;
        public event EventHandler RemoveAttachmentHandler;
        public event EventHandler AddAttachmentFromFileHandler;
        public event EventHandler SwapAttachmentHandler;


        public RelayCommand RemoveAttachmentCommand { get; set; }
        public RelayCommand AddAttachmentFromFileCommand { get; set; }
        public RelayCommand SwapAttachmentCommand { get; set; }


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

        string _nodeName;
        public string NodeName
        {
            get { return _nodeName; }
            set
            {
                if (_nodeName != value)
                {
                    _nodeName = value;
                    RaisePropertyChanged("NodeName");
                }
            }
        }

        string _propTextColor;
        public string PropTextColor
        {
            get { return _propTextColor; }
            set
            {
                if (_propTextColor != value)
                {
                    _propTextColor = value;
                    RaisePropertyChanged("PropTextColor");
                }
            }
        }

        PropFile _attachedProp;
        public PropFile AttachedProp
        {
            get { return _attachedProp; }
            set
            {
                _attachedProp = value ?? NullProp;
                PropTextColor = _attachedProp == NullProp ? "#cc0000" : "#00b214";

                AttributeStringEventArgs eventArgs = new AttributeStringEventArgs()
                {
                    NodeName = NodeName,
                    Attribute = "attached_file",
                    Value = _attachedProp.FilePath
                };
                AttributeChangedHandler?.Invoke(this, eventArgs);

                if (_attachedProp != NullProp)
                {
                    PropFileEventArgs propFileEventArgs = new PropFileEventArgs()
                    {
                        PropFile = _attachedProp
                    };
                    AddAttachmentHandler?.Invoke(this, propFileEventArgs);
                }

                RaisePropertyChanged("AttachedProp");
            }
        }

        PropAttachment _swapAttachment;
        public PropAttachment SwapAttachment
        {
            get { return _swapAttachment; }
            set
            {
                if(_swapAttachment != value)
                {
                    _swapAttachment = value;
                    RaisePropertyChanged("SwapAttachment");
                }
            }
        }


        public PropAttachment(string name, string nodeName)
        {
            Name = name;
            NodeName = nodeName;
            AttachedProp = null;
            PropTextColor = "#cc0000";

            RemoveAttachmentCommand = new RelayCommand(RemoveAttachmentCall);
            AddAttachmentFromFileCommand = new RelayCommand(AddAttachmentFromFileCall);
            SwapAttachmentCommand = new RelayCommand(SwapAttachmentCall);
        }


        public void RemoveAttachmentCall(object sender)
        {
            RemoveAttachmentHandler?.Invoke(this, null);
        }

        public void AddAttachmentFromFileCall(object sender)
        {
            using (OpenFileDialog filesDialog = new OpenFileDialog())
            {
                filesDialog.Title = "Load Prop FBX";
                filesDialog.Filter = "FBX file (*.fbx)|*.fbx;*.FBX";
                filesDialog.RestoreDirectory = true;

                DialogResult fileResult = filesDialog.ShowDialog();
                if (fileResult == DialogResult.OK)
                {
                    FilePathEventArgs eventArgs = new FilePathEventArgs()
                    {
                        FilePath = filesDialog.FileName
                    };
                    AddAttachmentFromFileHandler?.Invoke(this, eventArgs);
                }
            }
            
        }

        public void SwapAttachmentCall(object sender)
        {
            PropEventArgs eventArgs = new PropEventArgs()
            {
                Prop = (PropAttachment)sender
            };
            SwapAttachmentHandler?.Invoke(this, eventArgs);
        }


        public class FilePathEventArgs : EventArgs
        {
            public string FilePath = "";
        }

        public class PropEventArgs : EventArgs
        {
            public PropAttachment Prop = null;
        }

        public class PropFileEventArgs : EventArgs
        {
            public PropFile PropFile = null;
        }

        public class AttributeStringEventArgs : EventArgs
        {
            public string NodeName = "";
            public string Attribute = "";
            public string Type = "string";
            public string Value = "";
        }


        void RaisePropertyChanged(string prop)
        {
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(prop));
        }
        public event PropertyChangedEventHandler PropertyChanged;
    }
}
